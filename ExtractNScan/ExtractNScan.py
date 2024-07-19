import chromadb
from openai import OpenAI
import os
import subprocess
import time
import threading

# Ensure the OpenAI API key is set
api_key = os.getenv("OPENAI_API_KEY")

# Initialize the OpenAI client with the custom API endpoint
client = OpenAI()

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
    return collection, documents['documents']

# Function to generate and properly format the nmap command
def generate_nmap_command(ips_and_domains):
    prompt = f"Formulate a single bash nmap scan command for the following targets, make sure to only respond with just a single bash command: {ips_and_domains}"
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000
    )
    print(response)  # Debugging: Print the response to check its structure
    command = response.choices[0].message.content.strip()
    # Remove Markdown code block delimiters if present
    if command.startswith("```bash") and command.endswith("```"):
        command = command[7:-3].strip()  # Adjust indices to skip '```bash\n'
    return command

# Function to execute the nmap command
def run_nmap_scan(command):
    print(f"Running nmap command: {command}")  # Debugging: Print the command being run
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    print(f"nmap command stdout: {result.stdout}")  # Debugging: Print the standard output of the command
    print(f"nmap command stderr: {result.stderr}")  # Debugging: Print the standard error of the command
    return result.stdout

# Function to save scan results to ChromaDB
def save_scan_results_to_chromadb(collection, org_name, scan_results):
    document_id = f"{org_name.replace(' ', '_').lower()}_scan_{int(time.time())}"
    document_content = f"Organization Name: {org_name}\nScan Results:\n{scan_results}"
    document = {
        "id": document_id,
        "content": document_content,
        "metadata": {
            "scan_time": time.time(),
            "org_name": org_name
        }
    }
    # Prepare documents and ids for insertion
    documents = [document["content"]]
    ids = [document["id"]]
    collection.add(documents=documents, ids=ids)
    print(f"Scan results saved to ChromaDB collection '{collection.name}'.")

def show_progress():
    while True:
        for i in range(1, 4):
            print(f"\rScanning{'.' * i}", end="", flush=True)
            time.sleep(0.5)
        if stop_event.is_set():
            break

def main():
    print(cuddles_art())
    print("Starting the process to retrieve information and run nmap scan.")

    # Stage One: Connect to ChromaDB and retrieve data
    org_name = input("Please enter the organisation name to retrieve data: ")
    if not org_name:
        print("Organisation name is required. Exiting.")
        return

    collection, documents = get_chromadb_data(org_name)
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

    # Remove code block delimiters if present
    if nmap_command.startswith("```") and nmap_command.endswith("```"):
        nmap_command = nmap_command[3:-3].strip()

    # Start the progress display in a separate thread
    global stop_event
    stop_event = threading.Event()
    progress_thread = threading.Thread(target=show_progress)
    progress_thread.start()

    # Run the nmap scan
    scan_result = run_nmap_scan(nmap_command)
    
    # Stop the progress display
    stop_event.set()
    progress_thread.join()

    print("\nNmap scan results:")
    print(scan_result)

    print("Organization Name: ", org_name)
    print("Scan Results: ", scan_result)

    # Stage Three: Save the scan results to ChromaDB
    save_scan_results_to_chromadb(collection, org_name, scan_result)

if __name__ == "__main__":
    main()
