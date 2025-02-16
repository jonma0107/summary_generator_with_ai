![image](https://github.com/user-attachments/assets/cadc18da-3f35-4265-b91d-247fcd0120b6)

![image](https://github.com/user-attachments/assets/9551216e-24c4-4be5-9b3e-a15e4e113377)

![image](https://github.com/user-attachments/assets/dad9b869-df05-4f6e-a6c3-b2eabc1db33d)

![image](https://github.com/user-attachments/assets/f6f3e405-7ea6-4aff-bc93-5be7b0b1fe9a)

## Generate Summary from Transcription

This function prepares a request to the OpenAI API to generate a concise summary in the language needed from a given transcript.

### Function Definition

```python
def generate_summary_from_transcription(transcription):
    messages = [
        {"role": "system", "content": "You are a concise summary writer."},
        {"role": "user", "content": f"From the content of the generated transcript, make a summary in Spanish.\n\nTranscripción:\n{transcription}"}
    ]
