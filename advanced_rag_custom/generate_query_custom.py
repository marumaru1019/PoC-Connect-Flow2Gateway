from promptflow import tool
from promptflow.connections import CustomConnection
import requests

@tool
def call_custom_model(input_text: str, conn: CustomConnection) -> str:
    # カスタム接続から必要な情報を取得
    endpoint_url = conn.endpoint_url
    api_key = conn.sub_key

    system_messaage = '''
    あなたはAI言語モデルアシスタントです。  
    あなたの仕事は、ベクトル・データベースから関連文書を検索するために、与えられたユーザーの質問に対して異なるバージョンを生成することです。  
    ユーザの質問に対する複数の異なる視点を生成することによって、あなたのゴールは、ユーザが距離ベースの類似検索の制限のいくつかを克服するのを助けることです。  

    # タスク 
    - 改行で区切られた代替の質問を3つ考えてください。  
    - ユーザからの質問をもとに、観点ごとに「,」(半角カンマ)で区切られた、ドキュメントを検索するための検索クエリを3つの異なる観点で作成してください。 

    # 制約条件
    - 回答は、検索クエリのみとしてください。

    few-shot:
    Human: "結婚に必要な手続きを教えてください。"
    AI: 結婚 申請 手順,結婚式 場所,婚姻 手続き 期限
    '''

    messages = {"messages":[
        {"role": "system", "content": system_messaage},
        {"role": "user", "content": input_text}
    ]}

    # 例: 自作エンドポイントへリクエストを送る
    headers = {
        "Content-Type": "application/json",
        "api-key": f"{api_key}"
    }
    response = requests.post(endpoint_url, json=messages, headers=headers)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]