import chromadb
import os
import subprocess
import time
import threading
import paramiko
import sys

# Ensure the OpenAI API key is set
api_key = os.getenv("OPENAI_API_KEY")

# Function to display ASCII art
def cuddles_art():
    art = """
███████ ███████ ██   ██ 
██      ██      ██   ██ 
███████ ███████ ███████ 
     ██      ██ ██   ██ 
███████ ███████ ██   ██ 
                        
                                                                                                         
"""
    return art

# Function to connect to ChromaDB and retrieve collection data
def get_chromadb_data(collection_name):
    chromadb_client = chromadb.PersistentClient(path="./data")
    collection = chromadb_client.get_or_create_collection(name=collection_name.lower().replace(' ', '_'))
    # Fetching all documents from the collection
    documents = collection.get(ids=None)
    return collection, documents['documents']

# Function to parse nmap results for open ports
def parse_nmap_results(scan_results):
    open_ports = []
    for line in scan_results.split('\n'):
        if '/tcp' in line and 'open' in line:
            port = line.split('/')[0].strip()
            open_ports.append(int(port))
    return open_ports

# Function to attempt SSH login
def attempt_ssh_login(ip, credentials):
    for cred in credentials:
        username, password = cred.split(':')
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, port=22, username=username, password=password, timeout=5)
            print(f"Success: Logged in to {ip} with {username}:{password}")
            ssh.close()
            return True
        except paramiko.AuthenticationException:
            print(f"Failed: {username}:{password}")
        except Exception as e:
            print(f"Error: {str(e)}")
    return False

def main():
    print(cuddles_art())
    print("Starting the process to check SSH access using provided credentials.")

    # Retrieve organisation name from command-line arguments
    if len(sys.argv) != 2:
        print("Usage: python3 SSH.py <organisation_name>")
        return
    org_name = sys.argv[1]

    # Stage One: Connect to ChromaDB and retrieve data
    collection, documents = get_chromadb_data(org_name)
    if not documents:
        print(f"No data found for organisation '{org_name}'. Exiting.")
        return

    # Debugging: Print fetched documents to check their structure
    print("Fetched documents:", documents)

    # Extract IP addresses, nmap results, and credentials from documents
    ips_and_domains = []
    credentials = []
    scan_results = ""
    for doc in documents:
        print("Document text:", doc)  # Debugging: Print each document text
        if 'Known domains and IPs' in doc:
            ips_and_domains_str = doc.split('Known domains and IPs: ')[-1]
            ips_and_domains.extend(ips_and_domains_str.split(','))
        if 'Known credentials' in doc:
            credentials_str = doc.split('Known credentials: ')[-1]
            credentials.extend(credentials_str.split(','))
        if 'Scan Results:' in doc:
            scan_results = doc.split('Scan Results:\n')[-1]

    if not ips_and_domains:
        print(f"No IP addresses or domains found for organisation '{org_name}'. Exiting.")
        return

    if not credentials:
        print(f"No credentials provided for organisation '{org_name}'. Exiting.")
        return

    if not scan_results:
        print(f"No scan results found for organisation '{org_name}'. Exiting.")
        return

    # Parse the nmap results for open ports
    open_ports = parse_nmap_results(scan_results)
    print(f"Open ports: {open_ports}")

    # Check if port 22 is open
    if 22 in open_ports:
        for ip in ips_and_domains:
            print(f"Attempting SSH login to {ip}...")
            if attempt_ssh_login(ip, credentials):
                print(f"Successfully logged into {ip} via SSH.")
                return
        print("Failed to log into any IPs via SSH.")
    else:
        print("Port 22 is not open on any provided IPs.")

if __name__ == "__main__":
    main()
