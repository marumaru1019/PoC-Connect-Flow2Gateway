from promptflow import tool
from promptflow.connections import CustomConnection
import requests

@tool
def call_custom_model(chunk: str, filename: str, question: str, conn: CustomConnection) -> str:
    # カスタム接続から必要な情報を取得
    endpoint_url = conn.endpoint_url
    api_key = conn.sub_key

    system_messaage = '''
    あなたは、ユーザからの質問に答える、AIアシスタントです。
    あなたは、根拠となるドキュメント及びその中の重要なテキストをもとに、ユーザからの質問に答えてください。
    あなたは、根拠となるドキュメント及びその中の重要なテキストからの情報だけをもとに答えてください。
    回答の際は出典となる文書の一覧も出力してください。
    '''

    user_message = f'''
    # 重要な根拠テキスト
    {chunk}

    # 出典となる文書一覧
    {filename}

    # ユーザーからの質問
    {question} 

    # 回答
    '''

    messages = {"messages":[
        {"role": "system", "content": system_messaage},
        {"role": "user", "content": user_message}
    ]}

    # 例: 自作エンドポイントへリクエストを送る
    headers = {
        "Content-Type": "application/json",
        "api-key": f"{api_key}"
    }
    response = requests.post(endpoint_url, json=messages, headers=headers)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]