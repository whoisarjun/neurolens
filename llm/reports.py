from llm import chatbot

def generate(patient_data, days, model='mixtral'):
    summary = chatbot.chat(f'''
    Recent cognitive history: {patient_data['recent_cognitive_history']}
    Given the above cognitive metrics of a dementia patient, generate a brief summary of how the patient is doing.
    ''', model).split('</think>')[-1]

    metrics = chatbot.chat(f'''
    Recent cognitive history: {patient_data['recent_cognitive_history']}
    Summary of full timeline: {patient_data['yearly_summary']}
    Given the above cognitive metrics of a dementia patient, generate a few trends or insights you can detect, using bullet points. You do not have to include every feature - just those that seem important for the caregiver to know.
    ''', model).split('</think>')[-1]

    qn_history = chatbot.chat(f'''
    Recent question history: {patient_data['recent_question_history']}
    Given the questioning history of a dementia patient, write notes on how the patient answered recall questions — were they coherent, emotional, confused, etc. Ensure it is accurate based on the data provided.
    ''', model).split('</think>')[-1]

    recommendations = chatbot.chat(f'''
    Patient information: {patient_data['patient_info']}
    Summary: {summary}
    Cognitive metrics: {metrics}
    Questioning history: {qn_history}
    You are a cognitive health assistant. Using the given patient data, generate 3-5 recommendations caregivers can use to ensure better treatment/monitoring of the dementia patient. Do so with bullet points.
    ''', model).split('</think>')[-1]


    return f'''
# Neurolens Cognitive Report

## Patient Info
- Full Name: {patient_data['patient_info']['full_name']}
- Age: {patient_data['patient_info']['age']}
- Gender: {patient_data['patient_info']['gender'][0].upper()}
- Report Period: Last {days} days

## Summary
{summary}

## Cognitive Metrics Overview
{metrics}

## Question Interaction Summary
{qn_history}

## Recommendations
{recommendations}
        '''
