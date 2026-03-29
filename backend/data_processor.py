import pandas as pd
import os
from typing import List, Dict, Any
import re

class DataProcessor:
    def __init__(self):
        # Get the project root directory (parent of backend)
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(backend_dir)
        self.base_path = os.path.join(project_root, 'data')
        self.classrooms = pd.DataFrame()
        self.labs = pd.DataFrame()
        self.staffrooms = pd.DataFrame()
        self.load_all_datasets()
    
    def load_all_datasets(self):
        """Load the consolidated master CSV dataset"""
        try:
            # Use the consolidated file for labs, classrooms, and staffrooms
            master_path = os.path.join(self.base_path, 'dataset_tce.csv')
            
            if os.path.exists(master_path):
                # Load the single master file into a DataFrame
                df = pd.read_csv(master_path)
                # Clean column names - remove leading/trailing spaces
                df.columns = df.columns.str.strip()
                
                # Assign to all three so the existing search functions work
                self.classrooms = df
                self.labs = df
                self.staffrooms = df
                
                print(f"Loaded master dataset: {len(df)} rows, columns: {list(df.columns)}")
            else:
                print(f"Warning: Master dataset file not found at {master_path}")
        except Exception as e:
            print(f"Error loading datasets: {e}")
            import traceback
            traceback.print_exc()
    
    def search_classrooms(self, query: str) -> List[Dict[str, Any]]:
        """Search for classrooms matching the query"""
        if self.classrooms.empty:
            return []
        
        results = []
        query_lower = query.lower().strip()
        query_words = query_lower.split()
        
        # Get classroom name column
        classroom_col = None
        for col in self.classrooms.columns:
            col_lower = col.lower().strip()
            if 'classroom' in col_lower or ('name' in col_lower and 'classroom' in col_lower):
                classroom_col = col
                break
        
        if not classroom_col:
            for col in self.classrooms.columns:
                if 'name' in col.lower():
                    classroom_col = col
                    break
        
        if not classroom_col:
            return []
        
        # Create search mask
        mask = pd.Series([False] * len(self.classrooms))
        
        if classroom_col in self.classrooms.columns:
            name_mask = self.classrooms[classroom_col].astype(str).str.lower().str.contains(query_lower, na=False, regex=False)
            mask = mask | name_mask
            
            # Word-by-word matching
            for word in query_words:
                if len(word) > 2:
                    word_mask = self.classrooms[classroom_col].astype(str).str.lower().str.contains(word, na=False, regex=False)
                    mask = mask | word_mask
        
        matches = self.classrooms[mask].drop_duplicates()
        
        for _, row in matches.iterrows():
            results.append({
                'type': 'classroom',
                'name': str(row[classroom_col]).strip(),
                'department': str(row.get('Department Name', 'N/A')).strip() if pd.notna(row.get('Department Name', 'N/A')) else 'N/A',
                'block': str(row.get('Block Name', 'N/A')).strip() if pd.notna(row.get('Block Name', 'N/A')) else 'N/A',
                'floor': self._get_floor_display(row.get('Floor Number', 'N/A'))
            })
        
        return results
    
    def search_labs(self, query: str) -> List[Dict[str, Any]]:
        """Search for labs matching the query"""
        if self.labs.empty:
            return []
        
        results = []
        # Normalize: strip punctuation so "lab?" doesn't become regex that matches all labs
        query_lower = ' '.join(re.sub(r'[?\.,!;:\'"]+', ' ', query.lower().strip()).split())
        query_words = query_lower.split()
        
        # Get column names (handle variations)
        lab_col = None
        for col in self.labs.columns:
            col_lower = col.lower().strip()
            if ('lab' in col_lower and 'name' in col_lower) or col_lower == 'lab name':
                lab_col = col
                break
        
        if not lab_col:
            for col in self.labs.columns:
                if 'lab' in col.lower():
                    lab_col = col
                    break
        
        faculty_col = None
        for col in self.labs.columns:
            if 'faculty' in col.lower() and 'name' in col.lower():
                faculty_col = col
                break
        
        if not lab_col:
            return []
        
        # Create a combined search mask
        mask = pd.Series([False] * len(self.labs))
        
        # Search in lab names with better matching
        if lab_col in self.labs.columns:
            # Handle common abbreviations
            abbreviation_map = {
                'ml': 'machine learning',
                'ai': 'artificial intelligence',
                'iot': 'internet of things',
                'sse': 'smart and secure environment',
                'iba': 'integrated business application'
            }
            
            # Check if query is specific lab query (e.g., "agile lab", "ml lab", "sse lab")
            # Use len<=3 so "where is agile lab" uses else branch where "agile" matches only Agile Lab
            is_specific_lab_query = len(query_words) <= 3 and any(word in ('lab', 'laboratory') for word in query_words)
            
            if is_specific_lab_query:
                # For specific lab queries, prioritize exact matches
                lab_name_word = None
                for word in query_words:
                    if word != 'lab' and word != 'laboratory' and word not in abbreviation_map:
                        if len(word) > 2:  # Meaningful word
                            lab_name_word = word
                            break
                
                # Also check for abbreviations
                abbrev_word = None
                for word in query_words:
                    if word in abbreviation_map:
                        abbrev_word = word
                        break
                
                # First try exact word match
                if lab_name_word:
                    try:
                        exact_mask = self.labs[lab_col].astype(str).str.lower().str.contains(r'^' + lab_name_word + r'\b', na=False, regex=True)
                        mask = mask | exact_mask
                        # Also try if it starts with the word
                        starts_with_mask = self.labs[lab_col].astype(str).str.lower().str.startswith(lab_name_word)
                        mask = mask | starts_with_mask
                    except:
                        exact_mask = self.labs[lab_col].astype(str).str.lower().str.contains(lab_name_word, na=False, regex=False)
                        mask = mask | exact_mask
                
                # Handle abbreviation
                if abbrev_word:
                    full_form = abbreviation_map[abbrev_word]
                    try:
                        abbrev_mask = self.labs[lab_col].astype(str).str.lower().str.contains(r'\b' + full_form + r'\b', na=False, regex=True)
                        mask = mask | abbrev_mask
                    except:
                        abbrev_mask = self.labs[lab_col].astype(str).str.lower().str.contains(full_form, na=False, regex=False)
                        mask = mask | abbrev_mask
            else:
                # For general queries, use broader matching
                name_mask = self.labs[lab_col].astype(str).str.lower().str.contains(query_lower, na=False, regex=False)
                mask = mask | name_mask
                
                # Word-by-word matching (skip "lab"/"laboratory" - they match all and add no information)
                for word in query_words:
                    if len(word) > 2 and word not in ('lab', 'laboratory'):
                        try:
                            word_mask = self.labs[lab_col].astype(str).str.lower().str.contains(r'\b' + re.escape(word) + r'\b', na=False, regex=True)
                            mask = mask | word_mask
                        except Exception:
                            word_mask = self.labs[lab_col].astype(str).str.lower().str.contains(word, na=False, regex=False)
                            mask = mask | word_mask
                
                # Apply abbreviation expansion for general queries (e.g. "where is sse lab" -> Smart and Secure Environment Lab)
                for abbrev, full_form in abbreviation_map.items():
                    if abbrev in query_words:
                        try:
                            abbrev_mask = self.labs[lab_col].astype(str).str.lower().str.contains(r'\b' + full_form + r'\b', na=False, regex=True)
                            mask = mask | abbrev_mask
                        except Exception:
                            abbrev_mask = self.labs[lab_col].astype(str).str.lower().str.contains(full_form, na=False, regex=False)
                            mask = mask | abbrev_mask
                # "smart and secure lab" -> Smart and Secure Environment Lab only
                if 'smart' in query_words and 'secure' in query_words:
                    try:
                        phrase_mask = self.labs[lab_col].astype(str).str.lower().str.contains(r'\bsmart and secure environment\b', na=False, regex=True)
                        mask = mask | phrase_mask
                    except Exception:
                        phrase_mask = self.labs[lab_col].astype(str).str.lower().str.contains('smart and secure environment', na=False, regex=False)
                        mask = mask | phrase_mask
        
        # Search in faculty names - but only if query doesn't seem to be about a specific lab
        # If query contains "lab" or "laboratory", prioritize lab name matching
        is_lab_name_query = any(word in ['lab', 'laboratory'] for word in query_words)
        
        if faculty_col and faculty_col in self.labs.columns:
            # Only search faculty names if query doesn't appear to be a lab name query
            if not is_lab_name_query:
                # Voice/typo variations for faculty (e.g. gautham, gautam, kautam -> Gowtham)
                faculty_spelling = {
                    'gautham': ['gowtham', 'gowth'], 'gautam': ['gowtham', 'gowth'],
                    'kautam': ['gowtham', 'gowth'],
                    'subhashni': ['subhashni', 'subhashini'], 'subhashini': ['subhashni', 'subhashini'],
                    'suganthi': ['suganthi', 'sugantha'], 'sugantha': ['suganthi', 'sugantha'],
                    'siva': ['siva', 'sivanesan'], 'sivanesan': ['siva', 'sivanesan'],
                }
                # First try exact phrase matching in faculty names
                faculty_mask = self.labs[faculty_col].astype(str).str.lower().str.contains(query_lower, na=False, regex=False)
                mask = mask | faculty_mask
                
                # Word-by-word and spelling variations in faculty names
                for word in query_words:
                    if len(word) > 2:
                        try:
                            word_mask = self.labs[faculty_col].astype(str).str.lower().str.contains(r'\b' + re.escape(word) + r'\b', na=False, regex=True)
                            mask = mask | word_mask
                        except Exception:
                            word_mask = self.labs[faculty_col].astype(str).str.lower().str.contains(word, na=False, regex=False)
                            mask = mask | word_mask
                        for v in faculty_spelling.get(word.lower(), []):
                            try:
                                vm = self.labs[faculty_col].astype(str).str.lower().str.contains(r'\b' + re.escape(v) + r'\b', na=False, regex=True)
                                mask = mask | vm
                            except Exception:
                                vm = self.labs[faculty_col].astype(str).str.lower().str.contains(v, na=False, regex=False)
                                mask = mask | vm
        
        # Get unique matches
        matches = self.labs[mask].drop_duplicates()
        
        # Check if query is specifically asking for a lab (contains "lab" or "laboratory")
        is_lab_query = any(word in ['lab', 'laboratory'] for word in query_words)
        
        # If query is very specific (like "agile lab", "ml lab", "smart and secure lab"), filter to only exact matches
        if is_lab_query and len(query_words) <= 5 and len(matches) > 1:
            exact_matches = []
            
            # Extract lab name words (e.g., "agile" from "agile lab")
            lab_name_words = [w for w in query_words if w != 'lab' and w != 'laboratory' and w not in abbreviation_map and len(w) > 2]
            abbrev_words = [w for w in query_words if w in abbreviation_map]
            
            for _, row in matches.iterrows():
                lab_name = str(row[lab_col]).strip().lower()
                is_exact = False
                
                # Check exact match with lab name words (e.g., "agile")
                if lab_name_words:
                    for lab_word in lab_name_words:
                        # Check if lab name starts with the word (e.g., "agile lab" starts with "agile")
                        # Remove "lab" suffix from lab_name for comparison
                        lab_name_base = lab_name.replace(' lab', '').replace(' laboratory', '').strip()
                        if lab_name_base.startswith(lab_word) or lab_name.startswith(lab_word):
                            is_exact = True
                            break
                        # Also check if word appears as first word
                        elif lab_name.startswith(f'{lab_word} '):
                            is_exact = True
                            break
                
                # Check abbreviation expansion match (e.g., "ml" -> "machine learning")
                if abbrev_words and not is_exact:
                    for abbrev in abbrev_words:
                        full_form = abbreviation_map[abbrev]
                        # Check if full form appears in lab name
                        if full_form in lab_name:
                            is_exact = True
                            break
                
                if is_exact:
                    exact_matches.append(row)
            
            # If we have exact matches, ONLY return those; otherwise return all
            if exact_matches:
                matches = pd.DataFrame(exact_matches)
        
        for _, row in matches.iterrows():
            results.append({
                'type': 'lab',
                'name': str(row[lab_col]).strip(),
                'faculty': str(row.get('Faculty Name', 'N/A')).strip() if pd.notna(row.get('Faculty Name', 'N/A')) else 'N/A',
                'department': str(row.get('Department Name', 'N/A')).strip() if pd.notna(row.get('Department Name', 'N/A')) else 'N/A',
                'block': str(row.get('Block Name', 'N/A')).strip() if pd.notna(row.get('Block Name', 'N/A')) else 'N/A',
                'floor': self._get_floor_display(row.get('Floor Number', 'N/A'))
            })
        
        return results
    
    def search_staffrooms(self, query: str) -> List[Dict[str, Any]]:
        """Search for staffrooms matching the query"""
        if self.staffrooms.empty:
            return []
        
        results = []
        query_lower = query.lower().strip()
        query_words = query_lower.split()
        
        # Get staffroom name column
        staffroom_col = None
        for col in self.staffrooms.columns:
            col_lower = col.lower().strip()
            if 'staffroom' in col_lower or 'office' in col_lower:
                staffroom_col = col
                break
        
        if not staffroom_col and len(self.staffrooms.columns) > 0:
            staffroom_col = self.staffrooms.columns[0]
        
        faculty_col = None
        for col in self.staffrooms.columns:
            if 'faculty' in col.lower() and 'name' in col.lower():
                faculty_col = col
                break
        
        if not staffroom_col:
            return []
        
        # Create search mask
        mask = pd.Series([False] * len(self.staffrooms))
        
        # Search in staffroom names
        if staffroom_col in self.staffrooms.columns:
            name_mask = self.staffrooms[staffroom_col].astype(str).str.lower().str.contains(query_lower, na=False, regex=False)
            mask = mask | name_mask
            
            for word in query_words:
                if len(word) > 2:
                    word_mask = self.staffrooms[staffroom_col].astype(str).str.lower().str.contains(word, na=False, regex=False)
                    mask = mask | word_mask
        
        # Search in faculty names
        if faculty_col and faculty_col in self.staffrooms.columns:
            # First try exact phrase matching
            faculty_mask = self.staffrooms[faculty_col].astype(str).str.lower().str.contains(query_lower, na=False, regex=False)
            mask = mask | faculty_mask
            
            # Also try word-by-word matching with word boundaries
            for word in query_words:
                if len(word) > 2:
                    # Use word boundaries for better matching
                    word_mask = self.staffrooms[faculty_col].astype(str).str.lower().str.contains(r'\b' + word + r'\b', na=False, regex=True)
                    mask = mask | word_mask
            
            # Also try fuzzy matching for common misspellings and voice-to-text (key=user input, value=terms to search in DB)
            spelling_variations = {
                'subhashini': ['subhashni', 'subhashini', 'subhash', 'subashini'],
                'subashini': ['subhashni', 'subhashini', 'subhash', 'subashini'],
                'subhashni': ['subhashini', 'subhashni', 'subhash', 'subashini'],
                'gowtham': ['gowtham', 'gowth'],
                'gautham': ['gowtham', 'gowth'],
                'gautam': ['gowtham', 'gowth'],
                'kautam': ['gowtham', 'gowth'],
                'siva': ['siva', 'sivanesan', 'siv'],
                'sivanesan': ['siva', 'sivanesan', 'siv'],
                'kavitha': ['kavitha', 'kavita', 'kavith'],
                'yuvasini': ['yuvashini', 'yuvasini', 'yuvash'],
                'yuvashini': ['yuvasini', 'yuvashini', 'yuvash'],
                'sugantha': ['sugantha', 'suganthi'],
                'suganthi': ['suganthi', 'sugantha'],
                'janakiraman': ['janakiraman', 'janaki', 'raman'],
                'priya': ['priya', 'priy'],
                'karthiga': ['karthiga', 'karthig']
            }
            
            for word in query_words:
                if len(word) > 2:
                    # Use word boundaries for exact word matching - prioritize this
                    try:
                        word_mask = self.staffrooms[faculty_col].astype(str).str.lower().str.contains(r'\b' + word + r'\b', na=False, regex=True)
                        mask = mask | word_mask
                    except:
                        word_mask = self.staffrooms[faculty_col].astype(str).str.lower().str.contains(word, na=False, regex=False)
                        mask = mask | word_mask
                    
                    # Try spelling variations
                    if word in spelling_variations:
                        for variation in spelling_variations[word]:
                            try:
                                var_mask = self.staffrooms[faculty_col].astype(str).str.lower().str.contains(r'\b' + variation + r'\b', na=False, regex=True)
                                mask = mask | var_mask
                            except:
                                var_mask = self.staffrooms[faculty_col].astype(str).str.lower().str.contains(variation, na=False, regex=False)
                                mask = mask | var_mask
        
        matches = self.staffrooms[mask].drop_duplicates()
        
        for _, row in matches.iterrows():
            results.append({
                'type': 'staffroom',
                'name': str(row[staffroom_col]).strip(),
                'faculty': str(row.get('Faculty Name', 'N/A')).strip() if pd.notna(row.get('Faculty Name', 'N/A')) else 'N/A',
                'department': str(row.get('Department Name', 'N/A')).strip() if pd.notna(row.get('Department Name', 'N/A')) else 'N/A',
                'block': str(row.get('Block Name', 'N/A')).strip() if pd.notna(row.get('Block Name', 'N/A')) else 'N/A',
                'floor': self._get_floor_display(row.get('Floor Number', 'N/A'))
            })
        
        return results
    
    def _get_floor_display(self, floor_num: Any) -> str:
        """Convert floor number to human-readable format"""
        if pd.isna(floor_num):
            return 'N/A'
        
        try:
            floor = int(float(floor_num))
            floor_names = {
                0: 'Ground Floor',
                1: 'First Floor',
                2: 'Second Floor',
                3: 'Third Floor',
                4: 'Fourth Floor',
                5: 'Fifth Floor'
            }
            return floor_names.get(floor, f'Floor {floor}')
        except:
            return str(floor_num)
    
    def get_relevant_context(self, query: str) -> Dict[str, Any]:
        """Get relevant context from all datasets based on the query"""
        # Normalize: strip punctuation so "sse lab?" / "lab?" doesn't match all labs (regex "lab?" would match "lab")
        query = ' '.join(re.sub(r'[?\.,!;:\'"]+', ' ', query.lower().strip()).split())
        query_lower = query
        context_parts = []
        all_results = []
        
        # Determine what to search based on keywords
        is_lab_query = any(keyword in query_lower for keyword in ['lab', 'laboratory'])
        is_classroom_query = any(keyword in query_lower for keyword in ['classroom', 'class'])
        is_staffroom_query = any(keyword in query_lower for keyword in ['staffroom', 'staff room', 'office', 'mam', 'sir', 'faculty'])
        
        # If query mentions person names (mam, sir, faculty, etc.) or doesn't specify, search all
        has_person_keywords = any(keyword in query_lower for keyword in ['mam', 'sir', 'professor', 'prof', 'dr.', 'dr ', 'faculty', 'teacher'])
        
        # If no specific type mentioned, search all
        if not (is_lab_query or is_classroom_query or is_staffroom_query) or has_person_keywords:
            is_lab_query = is_classroom_query = is_staffroom_query = True
        
        if is_lab_query:
            lab_results = self.search_labs(query)
            if lab_results:
                context_parts.append("LABS:")
                for result in lab_results:
                    all_results.append(result)
                    faculty_info = f" Faculty: {result['faculty']}." if result.get('faculty') and result['faculty'] != 'N/A' else ""
                    context_parts.append(
                        f"- {result['name']} is located in {result['block']}, {result['floor']}. "
                        f"Department: {result['department']}.{faculty_info}"
                    )
        
        if is_classroom_query:
            classroom_results = self.search_classrooms(query)
            if classroom_results:
                context_parts.append("\nCLASSROOMS:")
                for result in classroom_results:
                    all_results.append(result)
                    context_parts.append(
                        f"- {result['name']} is located in {result['block']}, {result['floor']}. "
                        f"Department: {result['department']}."
                    )
        
        if is_staffroom_query:
            staffroom_results = self.search_staffrooms(query)
            if staffroom_results:
                context_parts.append("\nSTAFFROOMS:")
                for result in staffroom_results:
                    all_results.append(result)
                    faculty_info = f" Faculty: {result['faculty']}." if result.get('faculty') and result['faculty'] != 'N/A' else ""
                    context_parts.append(
                        f"- {result['name']} is located in {result['block']}, {result['floor']}. "
                        f"Department: {result['department']}.{faculty_info}"
                    )
        
        # Check if multiple results have the same faculty name (for clarification)
        needs_clarification = False
        if has_person_keywords and len(all_results) > 1:
            # Extract search name from query
            query_words = [w for w in query_lower.split() if w not in ['where', 'is', 'mam', 'sir', 'professor', 'prof', 'dr.', 'dr', 'faculty', 'the', 'a', 'an', 'find', 'show', 'locate']]
            search_names = [w for w in query_words if len(w) > 2]  # Get meaningful words
            
            if search_names:
                # Check if multiple results match the search name and are in different departments
                departments = set()
                matching_results = []
                
                for result in all_results:
                    faculty = result.get('faculty', '')
                    if faculty and faculty != 'N/A':
                        faculty_lower = str(faculty).lower()
                        # Check if any search name appears in faculty name
                        for search_name in search_names:
                            # Clean faculty name for comparison
                            faculty_clean = faculty_lower.replace('mr.', '').replace('ms.', '').replace('mrs.', '').replace('dr.', '').replace('professor', '').replace('prof.', '').strip()
                            # Check if search name matches any part of faculty name (avoid false matches)
                            faculty_words = set(faculty_clean.split())
                            matches = False
                            
                            # Exact word match
                            if search_name in faculty_words:
                                matches = True
                            else:
                                # Check if search_name is a meaningful part of any word
                                for word in faculty_words:
                                    if len(word) >= len(search_name) and search_name in word:
                                        # Only match if search_name is at least 4 chars OR starts the word
                                        if len(search_name) >= 4 or word.startswith(search_name):
                                            matches = True
                                            break
                            
                            # Also check fuzzy matches for common misspellings and voice-to-text
                            spelling_variations = {
                                'subhashini': ['subhashni', 'subhashini', 'subhash', 'subashini'],
                                'subashini': ['subhashni', 'subhashini', 'subhash', 'subashini'],
                                'subhashni': ['subhashini', 'subhashni', 'subhash', 'subashini'],
                                'gowtham': ['gowtham', 'gowth'],
                                'gautham': ['gowtham', 'gowth'],
                                'gautam': ['gowtham', 'gowth'],
                                'kautam': ['gowtham', 'gowth'],
                                'siva': ['siva', 'sivanesan', 'siv'],
                                'sivanesan': ['siva', 'sivanesan', 'siv'],
                                'kavitha': ['kavitha', 'kavita', 'kavith'],
                                'yuvasini': ['yuvashini', 'yuvasini', 'yuvash'],
                                'yuvashini': ['yuvasini', 'yuvashini', 'yuvash']
                            }
                            if not matches and search_name in spelling_variations:
                                for variation in spelling_variations[search_name]:
                                    if variation in faculty_clean:
                                        matches = True
                                        break
                            
                            if matches:
                                dept = result.get('department', '')
                                if dept:
                                    departments.add(dept)
                                    matching_results.append(result)
                                break
                
                # If same name found in multiple departments, need clarification
                if len(departments) > 1:
                    needs_clarification = True
        
        context_text = "\n".join(context_parts) if context_parts else "No matching locations found in the datasets."
        
        return {
            'context': context_text,
            'results': all_results,
            'needs_clarification': needs_clarification,
            'is_person_query': has_person_keywords
        }
