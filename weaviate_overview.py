import weaviate
import os
import weaviate.classes.config as wc
from weaviate.classes.init import Auth
from weaviate.classes.aggregate import GroupByAggregate
from dotenv import load_dotenv
from collections import Counter
import requests

load_dotenv()

def main():
    # Load config from .env
    config = {
        "weaviate_url": os.getenv("WEAVIATE_URL", ""),
        "weaviate_apikey": os.getenv("WEAVIATE_API_KEY", ""),
        "class_name": os.getenv("WEAVIATE_CLASS", "Bill"),
        "openai_apikey": os.getenv("OPENAI_APIKEY", ""),
    }

    headers = {"X-OpenAI-Api-Key": config.get("openai_apikey")} if config.get("openai_apikey") else {}
    auth = Auth.api_key(api_key=config.get("weaviate_apikey")) if config.get("weaviate_apikey") else None

    client = weaviate.connect_to_weaviate_cloud(
        cluster_url=config.get("weaviate_url"),
        auth_credentials=auth,
        headers=headers,
        additional_config=weaviate.config.AdditionalConfig(timeout=weaviate.config.Timeout(insert=300))
    )
    print(f"Conectado a Weaviate em {config.get('weaviate_url')}")

    class_name = config.get("class_name")
    if not client.collections.exists(class_name):
        print(f"Coleção '{class_name}' não existe.")
        client.close()
        return

    collection = client.collections.get(class_name)

    # Use GraphQL for total count, fetch limited for counts
    gql_query = f"""
    {{
      Aggregate {{
        {class_name} {{
          meta {{
            count
          }}
        }}
      }}
    }}
    """
    print(f"Executando query GraphQL: {gql_query}")
    url = f"https://{config.get('weaviate_url')}/v1/graphql"
    headers = {
        "Authorization": f"Bearer {config.get('weaviate_apikey')}",
        "Content-Type": "application/json"
    }
    data = {"query": gql_query}
    response = requests.post(url, json=data, headers=headers)
    print(f"Status code: {response.status_code}")
    if response.status_code != 200:
        print(f"Erro HTTP: {response.text}")
        client.close()
        return
    response_json = response.json()
    print(f"Resposta GraphQL: {response_json}")
    if "errors" in response_json:
        print(f"Erros na query: {response_json['errors']}")
        client.close()
        return
    agg_data = response_json.get("data", {}).get("Aggregate", {})
    total_count = agg_data.get(class_name, [{}])[0].get("meta", {}).get("count", 0)

    # Fetch limited sample for counts, only house and year properties
    objects = collection.query.fetch_objects(
        limit=1000,
        return_properties=["house", "year"]
    )
    house_counts = Counter(obj.properties.get('house') for obj in objects.objects if obj.properties.get('house'))
    year_counts = Counter(obj.properties.get('year') for obj in objects.objects if obj.properties.get('year'))

    print("Overview do Weaviate:")
    print(f"Total de registros: {total_count}")
    print(f"Registros por casa legislativa: {house_counts}")
    print(f"Registros por ano: {year_counts}")

    client.close()

if __name__ == '__main__':
    main()