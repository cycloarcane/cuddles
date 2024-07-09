import chromadb
from openai import OpenAI
import os
import subprocess

# Ensure the OpenAI API key is set
api_key = os.getenv("OPENAI_API_KEY")

# Initialize the OpenAI client with the custom API endpoint
client = OpenAI(
    api_key=api_key,
    base_url="https://place-waiting-cooper-ssl.trycloudflare.com/v1/"
)

# Function to display ASCII art
def cuddles_art():
    art = """
 ██████ ██    ██ ██████  ██████  ██      ███████ ███████     
██      ██    ██ ██   ██ ██   ██ ██      ██      ██          
██      ██    ██ ██   ██ ██   ██ ██      █████   ███████     
██      ██    ██ ██   ██ ██   ██ ██      ██           ██     
 ██████  ██████  ██████  ██████  ███████ ███████ ███████     
                                                             
                                                                                      
"""
    return art

# Function to connect to ChromaDB and retrieve collection data
def get_chromadb_data(collection_name):
    chromadb_client = chromadb.PersistentClient(path="./data")
    collection = chromadb_client.get_or_create_collection(name=collection_name.lower().replace(' ', '_'))
    # Fetching all documents from the collection
    documents = collection.get(ids=None)
    return documents['documents']

# Function to interact with the LLM to generate nmap command
def generate_nmap_command(ips_and_domains):
    prompt = f"Formulate a bash nmap scan command for the following targets: {ips_and_domains}"
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000
    )
    print(response)  # Debugging: Print the response to check its structure
    return response.choices[0].message.content.strip()

# Function to execute the nmap command
def run_nmap_scan(command):
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout

def main():
    print(cuddles_art())
    print("Starting the process to retrieve information and run nmap scan.")

    # Stage One: Connect to ChromaDB and retrieve data
    org_name = input("Please enter the organisation name to retrieve data: ")
    if not org_name:
        print("Organisation name is required. Exiting.")
        return

    documents = get_chromadb_data(org_name)
    if not documents:
        print(f"No data found for organisation '{org_name}'. Exiting.")
        return

    # Debugging: Print fetched documents to check their structure
    print("Fetched documents:", documents)

    # Extract IP addresses and domain names from documents
    ips_and_domains = []
    for doc in documents:
        print("Document text:", doc)  # Debugging: Print each document text
        if 'Known domains and IPs' in doc:
            # Extract the value after 'Known domains and IPs:'
            ips_and_domains_str = doc.split('Known domains and IPs: ')[-1]
            ips_and_domains.extend(ips_and_domains_str.split(','))

    if not ips_and_domains:
        print(f"No IP addresses or domains found for organisation '{org_name}'. Exiting.")
        return

    # Stage Two: Generate and run nmap scan using LLM
    nmap_command = generate_nmap_command(ips_and_domains)
    print(f"Generated nmap command: {nmap_command}")

    scan_result = run_nmap_scan(nmap_command)
    print("nmap scan results:")
    print(scan_result)

if __name__ == "__main__":
    main()
