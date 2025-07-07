from flask import Flask, request, jsonify
import openai

app = Flask(__name__)

@app.route('/process_patient_data', methods=['POST'])
def process_data():
    patient_data = request.get_json()

    if not patient_data:
        return jsonify({"error": "no data received"}), 400

    generated_questions = generate_followup_questions(patient_data)

    return jsonify({
        "questions": generated_questions,
        "summary": "Optional: Any key insights",
    })

def generate_followup_questions(data):
    prompt = f"Patient speech shows: {data['features_summary']}. Suggest 3 cognitive check-in questions."
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response["choices"][0]["message"]["content"]

if __name__ == '__main__':
    app.run(port=5000, debug=True)