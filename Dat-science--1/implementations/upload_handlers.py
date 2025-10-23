import csv
import json
import sqlite3
import requests
from typing import List, Dict, Any
from .handlers import UploadHandler


class JournalUploadHandler(UploadHandler):
    
    def pushDataToDb(self, path: str) -> bool:
        
            # Reading a CSV file
            journals_data = self._read_csv_file(path)
            if not journals_data:
                print(f"Error: Unable to read file {path}")
                return False
            
            # Loading data into Blazegraph
            return self._upload_to_blazegraph(journals_data)
    
    def _read_csv_file(self, path: str) -> List[Dict[str, Any]]:
        
        journals = []
        
        with open(path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                journal_data = {
                    'title': row['Journal title'],
                    'issn_print': row['Journal ISSN (print version)'],
                    'eissn': row['Journal EISSN (online version)'],
                    'languages': [lang for lang in row['Languages in which the journal accepts manuscripts'].split(', ')],
                    'publisher': row['Publisher'] if row['Publisher'] else None,
                    'seal': row['DOAJ Seal'] == 'Yes',
                    'licence': row['Journal license'],
                    'apc': row['APC'] == 'Yes'
                }
                journals.append(journal_data)

        return journals
    
    def _upload_to_blazegraph(self, journals_data: List[Dict[str, Any]]) -> bool:
        
        success_count = 0
        
        for journal in journals_data:
            sparql_query = self._build_single_journal_query(journal)
            
            response = requests.post(
                self._dbPathOrUrl,
                data={'update': sparql_query},
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            
            if response.status_code == 200:
                success_count += 1
            else:
                print(f"Error loading journal {journal.get('issn_print', 'unknown')}: {response.status_code}")
        
        if success_count > 0:
            print(f"Successfully loaded {success_count} out of {len(journals_data)} journals into Blazegraph")
            return True
        else:
            print("No journal could be loaded")
            return False
                
    
    def _build_insert_query(self, journals_data: List[Dict[str, Any]]) -> str:
        # Defining prefixes
        prefixes = """
        PREFIX doaj: <http://doaj.org/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        """
        
        # Forming the INSERT DATA block
        insert_data = "INSERT DATA {\n"
        
        for journal in journals_data:
            # We use ISSN as a journal identifier
            journal_id = journal['issn_print'] or journal['eissn']
            if not journal_id:
                continue
                
            journal_uri = f"<http://doaj.org/journal/{journal_id}>"
            
            # Add triplets for the journal
            insert_data += f"    {journal_uri} rdf:type doaj:Journal .\n"
            insert_data += f"    {journal_uri} doaj:title \"{self._escape_string(journal['title'])}\" .\n"
            
            if journal['issn_print']:
                insert_data += f"    {journal_uri} doaj:issn \"{journal['issn_print']}\" .\n"
            if journal['eissn']:
                insert_data += f"    {journal_uri} doaj:eissn \"{journal['eissn']}\" .\n"
            
            # Languages
            for lang in journal['languages']:
                insert_data += f"    {journal_uri} doaj:language \"{self._escape_string(lang)}\" .\n"
            
            # Publisher
            if journal['publisher']:
                insert_data += f"    {journal_uri} doaj:publisher \"{self._escape_string(journal['publisher'])}\" .\n"
            
            # DOAJ Seal
            insert_data += f"    {journal_uri} doaj:hasDOAJSeal \"{journal['seal']}\"^^xsd:boolean .\n"
            
            # License
            insert_data += f"    {journal_uri} doaj:licence \"{self._escape_string(journal['licence'])}\" .\n"
            
            # APC
            insert_data += f"    {journal_uri} doaj:hasAPC \"{journal['apc']}\"^^xsd:boolean .\n"
        
        insert_data += "}"
        
        return prefixes + insert_data
    
    def _build_single_journal_query(self, journal: Dict[str, Any]) -> str:
        # Defining prefixes
        prefixes = """
        PREFIX doaj: <http://doaj.org/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        """
        
        # We use ISSN as a journal identifier
        journal_id = journal['issn_print'] or journal['eissn']
        if not journal_id:
            return ""
            
        journal_uri = f"<http://doaj.org/journal/{journal_id}>"
        
        # Forming the INSERT DATA block
        insert_data = f"INSERT DATA {{\n"
        insert_data += f"    {journal_uri} rdf:type doaj:Journal .\n"
        insert_data += f"    {journal_uri} doaj:title \"{self._escape_string(journal['title'])}\" .\n"
        
        if journal['issn_print']:
            insert_data += f"    {journal_uri} doaj:issn \"{journal['issn_print']}\" .\n"
        if journal['eissn']:
            insert_data += f"    {journal_uri} doaj:eissn \"{journal['eissn']}\" .\n"
        
        # Languages
        for lang in journal['languages']:
            insert_data += f"    {journal_uri} doaj:language \"{self._escape_string(lang)}\" .\n"
        
        # Publisher
        if journal['publisher']:
            insert_data += f"    {journal_uri} doaj:publisher \"{self._escape_string(journal['publisher'])}\" .\n"
        
        # DOAJ Seal
        insert_data += f"    {journal_uri} doaj:hasDOAJSeal \"{journal['seal']}\" .\n"
        
        # License
        insert_data += f"    {journal_uri} doaj:licence \"{self._escape_string(journal['licence'])}\" .\n"
        
        # APC
        insert_data += f"    {journal_uri} doaj:hasAPC \"{journal['apc']}\" .\n"
        
        insert_data += "}"
        
        return prefixes + insert_data
    
    def _escape_string(self, text: str) -> str:
        return text.replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')


class CategoryUploadHandler(UploadHandler):
    
    def pushDataToDb(self, path: str) -> bool:
        
        # Reading a JSON file
        scimago_data = self._read_json_file(path)
        if not scimago_data:
            print(f"Error: Unable to read file {path}")
            return False
        
        # Creating tables and loading data
        return self._upload_to_sqlite(scimago_data)
    
    def _read_json_file(self, path: str) -> List[Dict[str, Any]]:
        with open(path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            return data
    
    def _upload_to_sqlite(self, scimago_data: List[Dict[str, Any]]) -> bool:
        conn = sqlite3.connect(self._dbPathOrUrl)
        cursor = conn.cursor()
        
        # Creating tables
        self._create_tables(cursor)
        
        # Loading data
        self._insert_data(cursor, scimago_data)
        
        conn.commit()
        conn.close()
        
        print(f"Data successfully loaded into SQLite database {self._dbPathOrUrl}")
        return True
    
    def _create_tables(self, cursor) -> None:
        # Table of areas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS areas (
                id TEXT PRIMARY KEY
            )
        ''')
        
        # Table of categories
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id TEXT PRIMARY KEY,
                quartile TEXT
            )
        ''')
        
        # Journal-category relationship table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS journal_categories (
                issn TEXT,
                category_id TEXT,
                quartile TEXT,
                PRIMARY KEY (issn, category_id),
                FOREIGN KEY (category_id) REFERENCES categories(id)
            )
        ''')
        
        # Journal-area relationship table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS journal_areas (
                issn TEXT,
                area_id TEXT,
                PRIMARY KEY (issn, area_id),
                FOREIGN KEY (area_id) REFERENCES areas(id)
            )
        ''')
    
    def _insert_data(self, cursor, scimago_data: List[Dict[str, Any]]) -> None:
        for entry in scimago_data:
            identifiers = entry.get('identifiers', [])
            categories = entry.get('categories', [])
            areas = entry.get('areas', [])
            
            # Insert areas
            for area in areas:
                cursor.execute('INSERT OR IGNORE INTO areas (id) VALUES (?)', (area,))
            
            # Insert categories
            for category in categories:
                category_id = category.get('id')
                quartile = category.get('quartile')
                cursor.execute('INSERT OR IGNORE INTO categories (id, quartile) VALUES (?, ?)', 
                             (category_id, quartile))
            
            # Insert links journal-category
            for issn in identifiers:
                for category in categories:
                    category_id = category.get('id')
                    quartile = category.get('quartile')
                    cursor.execute('INSERT OR IGNORE INTO journal_categories (issn, category_id, quartile) VALUES (?, ?, ?)',
                                 (issn, category_id, quartile))
            
            # Insert links journal-area
            for issn in identifiers:
                for area in areas:
                    cursor.execute('INSERT OR IGNORE INTO journal_areas (issn, area_id) VALUES (?, ?)',
                                 (issn, area))