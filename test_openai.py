from decouple import config
from openai import OpenAI

def test():
    api_key = config('OPENAI_API_KEY')
    print("Testing API Key:", api_key[:15] + "..." + api_key[-10:])
    client = OpenAI(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[{'role': 'user', 'content': 'Say test'}],
            max_tokens=10
        )
        print("Success! Response:")
        print(response.choices[0].message.content)
    except Exception as e:
        print("Error during API call:")
        print(e)

if __name__ == '__main__':
    test()
