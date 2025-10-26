# -*- coding: utf-8 -*-
"""
Query handlers for databases.
Contains classes: JournalQueryHandler, CategoryQueryHandler
"""

import requests
import sqlite3
import pandas as pd
from typing import List, Set, Optional
from sqlite3 import connect
from .handlers import QueryHandler
from .models import Journal, Category, Area


# =========================================================================
# Ekaterina's part
# =========================================================================

class JournalQueryHandler(QueryHandler):   

    def _escape_literal(self, value: str) -> str:

        if value is None:
            return ""
            
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def getById(self, entity_id: str) -> pd.DataFrame:

        try:
            escaped_id = self._escape_literal(entity_id)
            sparql_query = f'''
            PREFIX doaj: <http://doaj.org/>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            
            SELECT ?journal ?title ?issn ?eissn ?language ?publisher ?seal ?licence ?apc
            WHERE {{
                ?journal rdf:type doaj:Journal .
                OPTIONAL {{ ?journal doaj:issn ?issn }}
                OPTIONAL {{ ?journal doaj:eissn ?eissn }}
                FILTER (?issn = "{escaped_id}" || ?eissn = "{escaped_id}")
                OPTIONAL {{ ?journal doaj:title ?title }}
                OPTIONAL {{ ?journal doaj:language ?language }}
                OPTIONAL {{ ?journal doaj:publisher ?publisher }}
                OPTIONAL {{ ?journal doaj:hasDOAJSeal ?seal }}
                OPTIONAL {{ ?journal doaj:licence ?licence }}
                OPTIONAL {{ ?journal doaj:hasAPC ?apc }}
            }}
            '''

            return self._execute_sparql_query(sparql_query)

        except Exception as e:
            print(f"Error in getById: {e}")
            return pd.DataFrame()

    def getByIds(self, ids: List[str]) -> pd.DataFrame:

        if not ids:
            return pd.DataFrame()

        try:
            values_list = []
            for journal_id in ids:
                if journal_id:
                    escaped_id = self._escape_literal(journal_id)
                    values_list.append(f'"{escaped_id}"')

            if not values_list:
                return pd.DataFrame()

            values_string = " ".join(values_list)

            sparql_query = f'''
            PREFIX doaj: <http://doaj.org/>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            
            SELECT ?journal ?title ?issn ?eissn ?language ?publisher ?seal ?licence ?apc
            WHERE {{
                ?journal rdf:type doaj:Journal .
                OPTIONAL {{ ?journal doaj:issn ?issn }}
                OPTIONAL {{ ?journal doaj:eissn ?eissn }}
                VALUES ?wanted {{ {values_string} }}
                FILTER (?issn = ?wanted || ?eissn = ?wanted)
                OPTIONAL {{ ?journal doaj:title ?title }}
                OPTIONAL {{ ?journal doaj:language ?language }}
                OPTIONAL {{ ?journal doaj:publisher ?publisher }}
                OPTIONAL {{ ?journal doaj:hasDOAJSeal ?seal }}
                OPTIONAL {{ ?journal doaj:licence ?licence }}
                OPTIONAL {{ ?journal doaj:hasAPC ?apc }}
            }}
            '''

            return self._execute_sparql_query(sparql_query)

        except Exception as e:
            print(f"Error in getByIds: {e}")
            return pd.DataFrame()

    def getAllJournals(self) -> pd.DataFrame:
 
        try:
            sparql_query = '''
            PREFIX doaj: <http://doaj.org/>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            
            SELECT ?journal ?title ?issn ?eissn ?language ?publisher ?seal ?licence ?apc
            WHERE {
                ?journal rdf:type doaj:Journal .
                ?journal doaj:title ?title .
                OPTIONAL { ?journal doaj:issn ?issn }
                OPTIONAL { ?journal doaj:eissn ?eissn }
                OPTIONAL { ?journal doaj:language ?language }
                OPTIONAL { ?journal doaj:publisher ?publisher }
                OPTIONAL { ?journal doaj:hasDOAJSeal ?seal }
                OPTIONAL { ?journal doaj:licence ?licence }
                OPTIONAL { ?journal doaj:hasAPC ?apc }
            }
            ORDER BY ?title
            '''

            return self._execute_sparql_query(sparql_query)

        except Exception as e:
            print(f"Error in getAllJournals: {e}")
            return pd.DataFrame()

    def getJournalsWithTitle(self, partialTitle: str) -> pd.DataFrame:

        try:
            escaped_title = self._escape_literal(partialTitle)
            sparql_query = f'''
            PREFIX doaj: <http://doaj.org/>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            
            SELECT ?journal ?title ?issn ?eissn ?language ?publisher ?seal ?licence ?apc
            WHERE {{
                ?journal rdf:type doaj:Journal .
                ?journal doaj:title ?title .
                FILTER (CONTAINS(LCASE(?title), LCASE("{escaped_title}")))
                OPTIONAL {{ ?journal doaj:issn ?issn }}
                OPTIONAL {{ ?journal doaj:eissn ?eissn }}
                OPTIONAL {{ ?journal doaj:language ?language }}
                OPTIONAL {{ ?journal doaj:publisher ?publisher }}
                OPTIONAL {{ ?journal doaj:hasDOAJSeal ?seal }}
                OPTIONAL {{ ?journal doaj:licence ?licence }}
                OPTIONAL {{ ?journal doaj:hasAPC ?apc }}
            }}
            ORDER BY ?title
            '''
            
            return self._execute_sparql_query(sparql_query)

        except Exception as e:
            print(f"Error in getJournalsWithTitle: {e}")
            return pd.DataFrame()

    def getJournalsPublishedBy(self, partialName: str) -> pd.DataFrame:

        try:
            escaped_name = self._escape_literal(partialName)
            sparql_query = f'''
            PREFIX doaj: <http://doaj.org/>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            
            SELECT ?journal ?title ?issn ?eissn ?language ?publisher ?seal ?licence ?apc
            WHERE {{
                ?journal rdf:type doaj:Journal .
                ?journal doaj:title ?title .
                ?journal doaj:publisher ?publisher .
                FILTER (CONTAINS(LCASE(?publisher), LCASE("{escaped_name}")))
                OPTIONAL {{ ?journal doaj:issn ?issn }}
                OPTIONAL {{ ?journal doaj:eissn ?eissn }}
                OPTIONAL {{ ?journal doaj:language ?language }}
                OPTIONAL {{ ?journal doaj:hasDOAJSeal ?seal }}
                OPTIONAL {{ ?journal doaj:licence ?licence }}
                OPTIONAL {{ ?journal doaj:hasAPC ?apc }}
            }}
            ORDER BY ?title
            '''

            return self._execute_sparql_query(sparql_query)

        except Exception as e:
            print(f"Error in getJournalsPublishedBy: {e}")
            return pd.DataFrame()

    # =========================================================================
    # 🔵 ЗОНА ОТВЕТСТВЕННОСТИ DEVELOPER B - ФИЛЬТРЫ ЖУРНАЛОВ
    # =========================================================================
    
    #Return journals with specified licenses
    # (pd.DataFrame: DataFrame with found journals)
    def getJournalsWithLicense(self, licenses: Set[str]) -> pd.DataFrame:

        if not licenses:
            return self.getAllJournals()
        
        # Build the license filter
        escaped_licenses = [
            f'"{self._escape_literal(license)}"' for license in licenses if license
        ]

        if not escaped_licenses:
            return pd.DataFrame()
        
        license_filter = " || ".join(
            [f"?licence = {licence}" for licence in escaped_licenses]
        )

        sparql_query = f"""
        PREFIX doaj: <http://doaj.org/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            
        SELECT ?journal ?title ?issn ?eissn ?language ?publisher ?seal ?licence ?apc
        WHERE {{
            ?journal rdf:type doaj:Journal .
            ?journal doaj:title ?title .
            ?journal doaj:licence ?licence .
            FILTER ({license_filter})
            OPTIONAL {{ ?journal doaj:issn ?issn }}
            OPTIONAL {{ ?journal doaj:eissn ?eissn }}
            OPTIONAL {{ ?journal doaj:language ?language }}
            OPTIONAL {{ ?journal doaj:publisher ?publisher }}
            OPTIONAL {{ ?journal doaj:hasDOAJSeal ?seal }}
            OPTIONAL {{ ?journal doaj:hasAPC ?apc }}
        }}
        ORDER BY ?title
        """

        return self._execute_sparql_query(sparql_query)
            

    #Return journals that have Article Processing Charge (APC)
    # (pd.DataFrame: DataFrame with journals that have APC)
    def getJournalsWithAPC(self) -> pd.DataFrame:
        
        sparql_query = """
        PREFIX doaj: <http://doaj.org/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            
        SELECT ?journal ?title ?issn ?eissn ?language ?publisher ?seal ?licence ?apc
        WHERE {
            ?journal rdf:type doaj:Journal .
            ?journal doaj:title ?title .
            ?journal doaj:hasAPC "true"^^xsd:boolean .
            OPTIONAL { ?journal doaj:issn ?issn }
            OPTIONAL { ?journal doaj:eissn ?eissn }
            OPTIONAL { ?journal doaj:language ?language }
            OPTIONAL { ?journal doaj:publisher ?publisher }
            OPTIONAL { ?journal doaj:hasDOAJSeal ?seal }
            OPTIONAL { ?journal doaj:licence ?licence }
            OPTIONAL { ?journal doaj:hasAPC ?apc }
        }
        ORDER BY ?title
        """

        return self._execute_sparql_query(sparql_query)


    # Return journals that have DOAJ Seal
    # (pd.DataFrame: DataFrame with journals that have DOAJ Seal)

    def getJournalsWithDOAJSeal(self) -> pd.DataFrame:
        
        sparql_query = """
        PREFIX doaj: <http://doaj.org/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            
        SELECT ?journal ?title ?issn ?eissn ?language ?publisher ?seal ?licence ?apc
        WHERE {
            ?journal rdf:type doaj:Journal .
            ?journal doaj:title ?title .
            ?journal doaj:hasDOAJSeal "true"^^xsd:boolean .
            OPTIONAL { ?journal doaj:issn ?issn }
            OPTIONAL { ?journal doaj:eissn ?eissn }
            OPTIONAL { ?journal doaj:language ?language }
            OPTIONAL { ?journal doaj:publisher ?publisher }
            OPTIONAL { ?journal doaj:hasDOAJSeal ?seal }
            OPTIONAL { ?journal doaj:licence ?licence }
            OPTIONAL { ?journal doaj:hasAPC ?apc }
        }
        ORDER BY ?title
        """

        return self._execute_sparql_query(sparql_query)

    # Return journals that match any of the provided ISSNs or EISSNs
    def getJournalsByIssns(self, issns: Set[str]) -> pd.DataFrame:
        
        cleaned_ids = {issn for issn in issns if issn}
        if not cleaned_ids:
            return pd.DataFrame()

        values_clause = " ".join(
            f'"{self._escape_literal(issn)}"' for issn in sorted(cleaned_ids)
        )
        
        sparql_query = f"""
        PREFIX doaj: <http://doaj.org/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            
        SELECT ?journal ?title ?issn ?eissn ?language ?publisher ?seal ?licence ?apc
        WHERE {{
            VALUES ?targetId {{ {values_clause} }}
            ?journal rdf:type doaj:Journal .
            ?journal doaj:title ?title .
            OPTIONAL {{ ?journal doaj:issn ?issn }}
            OPTIONAL {{ ?journal doaj:eissn ?eissn }}
            OPTIONAL {{ ?journal doaj:language ?language }}
            OPTIONAL {{ ?journal doaj:publisher ?publisher }}
            OPTIONAL {{ ?journal doaj:hasDOAJSeal ?seal }}
            OPTIONAL {{ ?journal doaj:licence ?licence }}
            OPTIONAL {{ ?journal doaj:hasAPC ?apc }}
            BIND(COALESCE(?issn, ?eissn) AS ?anyId)
            FILTER (?anyId IN ({values_clause}))
        }}
        ORDER BY ?title
        """
        return self._execute_sparql_query(sparql_query)
    

    # =========================================================================
    # ОБЩИЙ МЕТОД - КАТЮХА
    # =========================================================================
    def _execute_sparql_query(self, sparql_query: str) -> pd.DataFrame:
        """
        Execute SPARQL query and return result as DataFrame.
        """
        try:
            response = requests.get(
                self._dbPathOrUrl,
                params={"query": sparql_query, "format": "json"},
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                bindings = data.get("results", {}).get("bindings", [])

                if not bindings:
                    return pd.DataFrame()

                # Простое преобразование в DataFrame
                rows = []
                for binding in bindings:
                    row = {}
                    for key, value in binding.items():
                        row[key] = value.get("value", "")
                    rows.append(row)

                return pd.DataFrame(rows)
            else:
                print(f"SPARQL query failed with status: {response.status_code}")
                return pd.DataFrame()

        except Exception as e:
            print(f"Error in _execute_sparql_query: {e}")
            return pd.DataFrame()


# =============================================================================
# 🔵 ЗОНА ОТВЕТСТВЕННОСТИ DEVELOPER B - ВЕСЬ КЛАСС CATEGORYQUERYHANDLER
# =============================================================================

# Handler for categories and areas queries in a relational SQLite database

class CategoryQueryHandler(QueryHandler):

    def getById(self, entity_id: str) -> pd.DataFrame:
        
        with connect(self._dbPathOrUrl) as conn:

            category_query = "SELECT id, quartile FROM categories WHERE id = ?"
            category_df = pd.read_sql_query(category_query, conn, params=(entity_id,))

            if not category_df.empty:
                return category_df

            area_query = "SELECT id FROM areas WHERE id = ?"
            area_df = pd.read_sql_query(area_query, conn, params=(entity_id,))
            return area_df

        
    # Return all categories from the database 
    # (pd.DataFrame: DataFrame with all categories)
    def getAllCategories(self) -> pd.DataFrame:
        
        with connect(self._dbPathOrUrl) as conn:

            query = "SELECT DISTINCT id, quartile FROM categories ORDER BY id"
            df = pd.read_sql_query(query, conn)
            return df

    # Return all areas from the database
    # (pd.DataFrame: DataFrame with all areas)
    def getAllAreas(self) -> pd.DataFrame:
        
        with connect(self._dbPathOrUrl) as conn:

            query = "SELECT DISTINCT id FROM areas ORDER BY id"
            df = pd.read_sql_query(query, conn)
            return df


    # Return categories with specified quartiles
    # (pd.DataFrame: DataFrame with found categories)
    def getCategoriesWithQuartile(self, quartiles: Set[str]) -> pd.DataFrame:
      
        with connect(self._dbPathOrUrl) as conn:

            if not quartiles:
                # If quartiles are not specified, return all categories
                query = "SELECT DISTINCT id, quartile FROM categories ORDER BY id"
                df = pd.read_sql_query(query, conn)
            else:
                # Building query with quartile filter
                placeholders = ",".join(["?" for _ in quartiles])
                query = f"SELECT DISTINCT id, quartile FROM categories WHERE quartile IN ({placeholders}) ORDER BY id"
                df = pd.read_sql_query(query, conn, params=list(quartiles))

            return df


    # Return categories assigned to specified areas
    # (pd.DataFrame: DataFrame with found categories)
    def getCategoriesAssignedToAreas(self, area_ids: Set[str]) -> pd.DataFrame:
        
        with connect(self._dbPathOrUrl) as conn:

            if not area_ids:
                # If areas are not specified, return all categories
                query = """
                SELECT DISTINCT c.id, c.quartile 
                FROM categories c 
                ORDER BY c.id
                """
                df = pd.read_sql_query(query, conn)
            else:
                # Build query with area filter
                placeholders = ",".join(["?" for _ in area_ids])
                query = f"""
                SELECT DISTINCT c.id, c.quartile 
                FROM categories c
                JOIN journal_categories jc ON c.id = jc.category_id
                JOIN journal_areas ja ON jc.issn = ja.issn
                WHERE ja.area_id IN ({placeholders})
                ORDER BY c.id
                """
                df = pd.read_sql_query(query, conn, params=list(area_ids))

            return df

    # Return areas assigned to specified categories
    # (pd.DataFrame: DataFrame with found areas)

    def getAreasAssignedToCategories(self, category_ids: Set[str]) -> pd.DataFrame:
        
        with connect(self._dbPathOrUrl) as conn:

            if not category_ids:
                # If categories are not specified, return all areas
                query = "SELECT DISTINCT id FROM areas ORDER BY id"
                df = pd.read_sql_query(query, conn)
            else:
                # Build query with category filter
                placeholders = ",".join(["?" for _ in category_ids])
                query = f"""
                SELECT DISTINCT a.id 
                FROM areas a
                JOIN journal_areas ja ON a.id = ja.area_id
                JOIN journal_categories jc ON ja.issn = jc.issn
                WHERE jc.category_id IN ({placeholders})
                ORDER BY a.id
                """
                df = pd.read_sql_query(query, conn, params=list(category_ids))

            return df
