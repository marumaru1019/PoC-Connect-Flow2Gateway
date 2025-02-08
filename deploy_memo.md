# 前提条件
- Azure CLI がインストールされていること
- Docker for Linux がインストールされており、起動していること (docker -v でバージョンが表示されること)
- Azure CLI でログインしていること (az login でログイン)
- Python 3.9 以上がインストールされていること

# 環境セットアップ
## フローの置き換え
advanced_rag_custom/flow.dag.sample.yml を advanced_rag_custom/flow.dag.yml にリネーム

## 仮想環墧の作成
python -m venv .venv

## 仮想環境の有効化
source venv/bin/activate
.venv/Scripts/Activate.ps1

## ライブラリのインストール
pip install -r requirements.txt

## pf コマンドが有効になっているか確認
pf --version

# Flow の作成/動作確認
## コネクションの作成
pf connection create -f custom.yml --set configs.endpoint="AI Gateway のエンドポイント" secrets.sub_key="AI Gateway のサブスクリプションキー"

コメント
- AI Gateway のエンドポイントは "https://{APIM のリソース名}.azure-api.net/openai/deployments/{モデルのデプロイ名}/chat/completions?api-version={API バージョン}" のような形式

## フローの変更
flow.dag.yml の index lookup(lookup00 の箇所) ノードを自身の環境の値に置き換えます。
下記の箇所
```
- name: lookup00
  type: python
  source:
    type: package
    tool: promptflow_vectordb.tool.common_index_lookup.search
  inputs:
    mlindex_content: >
...
```

コメント
確認方法
![Image](https://github.com/user-attachments/assets/4b4b6280-89ab-46fa-9079-bcbfe8d91ef0)

## フローの動作確認
pf flow serve --source .\advanced_rag_custom --port 8080

コメント
localhost:8080 にアクセスして動作確認
何かしら

# デプロイ
## リソースグループの作成
az group create --name "リソースグループ" --location japaneast

## ACR を管理者ユーザーオンで作成
az acr create --resource-group "リソースグループ" --name "ACR名" --sku Standard --admin-enabled true --location japaneast

## フローのビルド
pf flow build --source　.\advanced_rag_custom --output dist --format docker

## ビルドされたフローのコネクションから不要な情報を削除
dist/connections/custom.yml の api-key の行を削除
```
$schema: 
  https://azuremlschemas.azureedge.net/promptflow/latest/CustomConnection.schema.json
type: custom
name: custom_connection_custom
configs:
  key1: test1
  endpoint_url: 
    エンドポイントの URL
secrets:
  api-key: ${env:CUSTOM_CONNECTION_CUSTOM_API-KEY} ← この行を削除
  sub_key: ${env:CUSTOM_CONNECTION_CUSTOM_SUB_KEY}
module: promptflow.connections
```

dist/settings.json の api-key の行を削除
```
{
  "CUSTOM_CONNECTION_CUSTOM_API-KEY": "", ← この行を削除
  "CUSTOM_CONNECTION_CUSTOM_SUB_KEY": ""
}
```


## フローのデプロイ
.\deploy.ps1 -Path dist -i sample-app:v1 -n "App Service のリソース名" -r "ACR のリソース名"azurecr.io
 -g "リソースグループ名" -l japaneast -sku "SKU の名前"

## App Service の環境変数の設定
Azure Portal にアクセスして、 `CUSTOM_CONNECTION_CUSTOM_SUB_KEY` の値を AI Gateway のサブスクリプションキーに設定
また、 `BUILD_INFO` の値を `{"build_number": "1"}` に設定
![Image](https://github.com/user-attachments/assets/74102de3-acae-438a-9ed5-0c68fe3b3b38)

## App Service に ML ワークスペースの閲覧権限を付与
### App Service のマネージド ID を有効化
Azure Portal にアクセスして、App Service の設定画面に移動
設定 > ID からマネージド ID を有効化
![Image](https://github.com/user-attachments/assets/5d0c4f2a-b793-4229-a615-ef9357a05654)

### ML データサイエンティストのロールを App Service に付与
Azure Portal にアクセスして、AI Foundry が存在するリソースグループに移動
アクセス制御 (IAM) > ロールの割り当ての追加
ロールの割り当ての追加画面で、ML データ科学者のロールを選択し、App Service のマネージド ID を選択

ロール割り当てを選択
![Image](https://github.com/user-attachments/assets/a14c6b0a-7835-4776-8f72-df803517976e)

Azure ML データ科学者のロールを選択
![Image](https://github.com/user-attachments/assets/b483994a-00b6-4e16-9fc5-ebb9126fc746)

App Service のマネージド ID を選択
![Image](https://github.com/user-attachments/assets/221509b4-6762-4cfe-be4f-871e0f69eca9)


付与までの時間がかかるため、少し待つ

## App Service の URL にアクセスして動作確認
https://{App Service のリソース名}.azurewebsites.net にアクセスして動作確認

![Image](https://github.com/user-attachments/assets/dac881c9-5431-4228-ae30-287b645ae7c1)

# その後の作業
- クエリ分割した後のフローが 1 つになっているため、プロジェクトの要件に合わせてクエリ拡張を行う