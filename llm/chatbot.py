import ollama
import os
import time
import traceback

PROMPTS_DIR = os.path.join(os.path.dirname(__file__), 'prompts')
QUESTION_COUNT = 5
QUESTION_GENERATION_MAX_ATTEMPTS = 3

def load_prompt(prompt_name, **kwargs):
    prompt_path = os.path.join(PROMPTS_DIR, prompt_name)
    try:
        with open(prompt_path, 'r', encoding='utf-8') as prompt_file:
            template = prompt_file.read().strip()
    except FileNotFoundError as exc:
        raise FileNotFoundError(f'Missing prompt file: {prompt_path}') from exc
    return template.format(**kwargs)

def chat(prompt=None, model='mixtral', verbose=True, messages=None):
    if verbose:
        print(f'[LLM] Sending prompt to model={model}...', flush=True)
    started_at = time.perf_counter()
    if messages is None:
        if prompt is None:
            raise ValueError('Either prompt or messages must be provided.')
        messages = [{
            'role': 'user',
            'content': prompt
        }]
    try:
        response = ollama.chat(
            model=model,
            messages=messages
        )
    except Exception as exc:
        elapsed = time.perf_counter() - started_at
        if verbose:
            print(f'[LLM] Request failed after {elapsed:.2f}s: {exc}', flush=True)
            print(traceback.format_exc(), flush=True)
        raise

    elapsed = time.perf_counter() - started_at
    if verbose:
        print(f'[LLM] Response obtained in {elapsed:.2f}s.', flush=True)
    return response['message']['content']

def _normalize_question_line(line):
    return line.lstrip(" -*\t0123456789.)(").strip()

def _parse_questions(response):
    return [
        _normalize_question_line(line)
        for line in response.splitlines()
        if _normalize_question_line(line)
    ]

def _validate_questions(questions):
    if len(questions) != QUESTION_COUNT:
        return False
    lowered = [question.casefold() for question in questions]
    return len(set(lowered)) == len(lowered)

def _build_question_retry_messages(patient_data, invalid_response):
    base_prompt = load_prompt(
        'question_generation.txt',
        patient_data=patient_data,
        question_count=QUESTION_COUNT,
    )
    retry_prompt = load_prompt(
        'question_generation_retry.txt',
        invalid_response=invalid_response,
        question_count=QUESTION_COUNT,
    )
    return [
        {'role': 'user', 'content': base_prompt},
        {'role': 'assistant', 'content': invalid_response},
        {'role': 'user', 'content': retry_prompt},
    ]

def new_questions(patient_data, model='mixtral'):
    prompt = load_prompt(
        'question_generation.txt',
        patient_data=patient_data,
        question_count=QUESTION_COUNT,
    )
    print(f"[LLM] Generating new questions for patient_id={patient_data.get('id')}", flush=True)
    raw_outputs = []

    for attempt in range(1, QUESTION_GENERATION_MAX_ATTEMPTS + 1):
        if attempt == 1:
            response = chat(prompt=prompt, model=model)
        else:
            print(
                f'[LLM] Retrying question generation attempt {attempt}/{QUESTION_GENERATION_MAX_ATTEMPTS}.',
                flush=True,
            )
            response = chat(
                model=model,
                messages=_build_question_retry_messages(patient_data, raw_outputs[-1]),
            )

        raw_outputs.append(response)
        questions = _parse_questions(response)
        print(f'[LLM] Parsed {len(questions)} questions on attempt {attempt}.', flush=True)

        if _validate_questions(questions):
            return questions

    raise ValueError(
        f'Failed to generate exactly {QUESTION_COUNT} unique questions after '
        f'{QUESTION_GENERATION_MAX_ATTEMPTS} attempts. Raw outputs: {raw_outputs}'
    )

def summarize_image(image_path, model='gemma4:e4b', verbose=True):
    prompt = load_prompt('image_summary.txt')

    if verbose:
        print(
            f"[LLM] Summarizing image with model={model}, file={os.path.basename(image_path)}...",
            flush=True,
        )

    started_at = time.perf_counter()
    try:
        response = ollama.chat(
            model=model,
            messages=[{
                'role': 'user',
                'content': prompt,
                'images': [image_path],
            }]
        )
    except Exception as exc:
        elapsed = time.perf_counter() - started_at
        if verbose:
            print(f'[LLM] Image summarization failed after {elapsed:.2f}s: {exc}', flush=True)
            print(traceback.format_exc(), flush=True)
        raise

    elapsed = time.perf_counter() - started_at
    summary = response['message']['content'].strip()
    if verbose:
        print(f'[LLM] Image summary obtained in {elapsed:.2f}s.', flush=True)
    return summary

def generate_report(patient_data, days=7, model='mixtral'):
    prompt = load_prompt(
        'report_generation.txt',
        recent_cognitive_history=patient_data['recent_cognitive_history'],
        yearly_summary=patient_data['yearly_summary'],
        recent_question_history=patient_data['recent_question_history'],
        full_name=patient_data['patient_info']['full_name'],
        age=patient_data['patient_info']['age'],
        gender=patient_data['patient_info']['gender'][0].upper(),
        days=days,
    )
    response = chat(prompt, model)
    return response.split('</think>')[-1]
