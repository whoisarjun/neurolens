import ollama

def chat(prompt, model='mixtral', verbose=True):
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

def new_questions(patient_data, model='mixtral'):
    prompt = f'''
    You are an expert cognitive health assistant. Your job is to generate exactly 5 memory recall questions to ask an elderly patient at risk for dementia.

    Patient data:
    {patient_data}

    Your questions must adhere to the following for them to be valid:
    - Help the patient recall specific events or experiences from their past (short-term or long-term).
    - Avoid all reasoning, productivity, work, or technology-related topics.
    - Some questions should be emotionally engaging and personally meaningful (e.g., family, school, food, friends, places, holidays, etc).
    - Combine a mixture of short-term (i.e. memories from the day or the week) and long-term memory questions (i.e. memories from the year or their childhood).
    - Of the 5 questions:
        - At least 2 must be focused on short-term memory (e.g. events from today or this week)
        - At least 2 must be focused on long-term memory (e.g. events from childhood, past holidays, old routines)
        - 1 can be either.
    - You should act as if you are a friend to the user.
    - Do NOT include your internal thoughts, planning steps, or commentary — only output the questions. Literally JUST the questions and NOTHING else.
    - Output exactly 5 questions separated by newline characters (\n), no numbering or bullet points.
    - The user will be reading these questions the next day.
    - Remember that the user is likely an elderly person at risk or suffering with dementia, so your questions should be simple to understand and not complex.
    - Do NOT repeat any questions that have been asked in the patient's question history. Use the question_history provided in the patient data to ensure all questions are fresh and unique. Repeating a question that has already been asked is considered a failure of the task.

    Example format:
    What is your favorite childhood memory?\nWhat was the last meal you really enjoyed?\n...
    '''
    response = chat(prompt, model)
    return [q.lstrip(" 0123456789.)").strip() for q in response.split('\n')[-5:] if q.strip()]

def generate_report(patient_data, days=7, model='mixtral'):
    prompt = f'''
    You are a cognitive health assistant. Using the following patient data, generate a structured report summarizing cognitive patterns over the past {days} days.
    Your job is not to replace the role of a doctor, but instead to provide the caregiver with a clear idea of how the patient is doing, and any useful information or insights that can aid the patient in dementia treatment.
    Do not include ANY internal thinking. All that is required is a report of the patient's cognitive data.
    
    Use Markdown formatting with clear sections:
    
    # Neurolens Cognitive Report
    
    ## Patient Info
    - Full Name: {patient_data['full_name']}
    - Age: {patient_data['age']}
    - Gender: {patient_data['gender'][0].upper()}
    - Report Period: Last {days} days
    
    ## Summary
    (A brief 3-5 sentence natural-language summary)
    
    ## Cognitive Metrics Overview
    - Speech Speed: (trend or insight)
    - Vocabulary Richness: (trend or insight)
    - Pause Duration: (trend or insight)
    ... (continue with the rest of the features)
    
    ## Detailed Trends (Day-by-Day)
    | Day | Speech Speed | Pauses | Vocab Richness | Filler Word Rate | Semantic Similarity Drift | Notes |
    |-----|---------------|--------|----------------|------------------|---------------------------|-------|
    | 1   | 4.3           | 30     | 0.45           | 0.02             | 0.02                      | Normal |
    | 2   | ...           | ...    | ...            | ...              | ...                       | ...   |
    
    ## Question Interaction Summary
    (Brief notes on how the patient answered recall questions — were they coherent, emotional, confused, etc. Ensure it is accurate based on the data provided.)
    
    ## Recommendations
    - Keep monitoring for (x)
    - Consider (y)
    ... (continue with actual insights and real recommendations)
    '''
    response = chat(prompt, model)
    return response.split('</think>')[-1]
