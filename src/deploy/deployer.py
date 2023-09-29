import subprocess
import time

from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport

TOKEN = ""

OWNER = "RobertRosca"
REPO_NAME = "zulip-write-only-proxy"

headers = {
    "Authorization": f"bearer {TOKEN}",
    "Accept": "application/vnd.github.flash-preview+json",
}
transport = AIOHTTPTransport(url="https://api.github.com/graphql", headers=headers)
client = Client(transport=transport, fetch_schema_from_transport=True)

query_string = f"""
query {{
    repository(owner: "{OWNER}", name: "{REPO_NAME}") {{
        deployments(last: 1, environments: ["staging"]) {{
        edges {{
            node {{
            id
            state
            environment
            latestStatus {{
                state
                description
            }}
            creator {{
                login
            }}
            }}
        }}
        }}
    }}
}}
"""
query = gql(query_string)


def update_deployment_status(deployment_id, state, description):
    mutation_string = f"""
    mutation {{
        createDeploymentStatus(input: {{
            deploymentId: "{deployment_id}"
            state: {state}
            description: "{description}"
        }}) {{
            clientMutationId
        }}
    }}
    """
    print(mutation_string)
    mutation = gql(mutation_string)
    client.execute(mutation)


prev_deployment_id = None

while True:
    result = client.execute(query)

    edges = result["repository"]["deployments"]["edges"]
    if len(edges) == 0:
        print("No deployments found")
        time.sleep(10)
        continue

    deployment = edges[0]["node"]
    deployment_id = deployment["id"]

    print(deployment)

    if deployment_id != prev_deployment_id and deployment["state"] == "IN_PROGRESS":
        # Update the deployment status to "IN_PROGRESS" on GitHub
        update_deployment_status(
            deployment_id, "IN_PROGRESS", "Pulling new Docker image"
        )
        time.sleep(5)
        update_deployment_status(deployment_id, "SUCCESS", "Done")

        try:
            subprocess.check_call(
                ["docker", "stack", "deploy", "-c", "docker-compose.yml", "zwop"]
            )

            update_deployment_status(
                deployment_id, "SUCCESS", "Deployment completed successfully"
            )

            print(f"New deployment detected: {deployment_id}")

            prev_deployment_id = deployment_id

        except Exception as e:
            update_deployment_status(deployment_id, "ERROR", str(e))
            print(f"Error during deployment: {e}")

    time.sleep(10)
