import ollama

def chat(prompt, model='mistral', verbose=True):
    if verbose:
        print(f'[LLM] Sending prompt...')
    response = ollama.chat(
        model=model,
        messages=[{
            'role': 'user',
            'content': prompt
        }]
    )
    if verbose:
        print(f'[LLM] Response obtained.')
    return response['message']['content']
