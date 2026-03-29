import os
from typing import Optional, Dict, List, Any
from openai import OpenAI
import json
import pandas as pd

class LLMService:
    def __init__(self, data_processor):
        self.data_processor = data_processor
        # Initialize OpenAI client - you can replace this with other LLM providers
        api_key = os.getenv('OPENAI_API_KEY', '')
        if api_key:
            self.client = OpenAI(api_key=api_key)
        else:
            self.client = None
            print("Warning: OPENAI_API_KEY not set. Using fallback response generation.")
    
    def generate_response(self, user_query: str, context_data: dict) -> str:
        """Generate response using LLM with context from datasets"""
        user_query_lower = user_query.lower().strip()
        
        # Handle greetings and general queries
        greetings = ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening', 'greetings', 'hi there']
        # Check for exact greeting or greeting at the start
        is_greeting = (user_query_lower in greetings or 
                      user_query_lower.startswith('hi ') or 
                      user_query_lower == 'hi' or
                      any(user_query_lower.startswith(g + ' ') or user_query_lower == g for g in greetings if len(g) > 2))
        if is_greeting:
            return "Hello! I'm TCE Compass, your AI-driven campus navigator. I can help you find:\n\n" \
                   "• Classrooms\n• Labs\n• Staffrooms\n• Faculty members\n\n" \
                   "Try asking me questions like:\n" \
                   "- Where is Agile Lab?\n" \
                   "- Show me the location of IG1 classroom\n" \
                   "- Where is Subhashni mam?\n" \
                   "- Find Siva sir\n\n" \
                   "How can I help you today?"
        
        context = context_data.get('context', '')
        results = context_data.get('results', [])
        needs_clarification = context_data.get('needs_clarification', False)
        is_person_query = context_data.get('is_person_query', False)
        
        # Check if query specifies a department
        dept_keywords = {
            'csbs': 'Computer Science and Business Systems',
            'computer science and business systems': 'Computer Science and Business Systems',
            'it': 'Information Technology',
            'information technology': 'Information Technology',
            'amcs': 'Applied Mathematics and Computational Science',
            'applied mathematics and computational science': 'Applied Mathematics and Computational Science',
            'computer applications': 'Computer Applications'
        }
        
        specified_dept = None
        dept_mentioned_in_query = False
        for key, dept_name in dept_keywords.items():
            if key in user_query_lower:
                specified_dept = dept_name
                dept_mentioned_in_query = True
                break
        
        # If department is specified, filter results - but only keep those matching the person query too
        if specified_dept and results:
            # Extract the person name from query (remove department keywords)
            query_words = [w for w in user_query_lower.split() 
                          if w not in ['from', 'dept', 'department', 'in', 'of', 'the'] 
                          and w not in dept_keywords.keys()]
            person_query_words = [w for w in query_words 
                                 if w not in ['sir', 'mam', 'professor', 'prof', 'dr', 'faculty', 'teacher']]
            
            filtered_results = []
            for r in results:
                # Must match department
                if r.get('department', '').lower() != specified_dept.lower():
                    continue
                
                # If person query, must also match faculty name
                if is_person_query and person_query_words:
                    faculty = str(r.get('faculty', '')).lower()
                    # Check if any person query word appears in faculty name
                    if any(word in faculty for word in person_query_words if len(word) > 2):
                        filtered_results.append(r)
                else:
                    filtered_results.append(r)
            
            if filtered_results:
                results = filtered_results
                needs_clarification = False
                context_data['results'] = results
                context_data['needs_clarification'] = False
        
        # For person queries with multiple results, check if clarification is needed
        if is_person_query and len(results) > 1 and not specified_dept:
            departments = set([r.get('department', '') for r in results])
            # If multiple departments and needs clarification, ask for clarification
            if len(departments) > 1 and needs_clarification:
                return self._generate_clarification_response(user_query, results)
            # Otherwise, show all results nicely formatted (user wants to see all)
        
        # If no API key, use a simple rule-based response
        if not self.client:
            return self._generate_fallback_response(user_query, context_data)
        
        try:
            # Create system prompt
            system_prompt = """You are TCE Compass, an AI-driven smart campus navigator assistant for TCE (Thiagarajar College of Engineering). 
Your role is to help students, faculty, and visitors find locations on campus.

You have access to three datasets:
1. Classrooms dataset - contains classroom locations
2. Labs dataset - contains laboratory locations  
3. Staffrooms dataset - contains staffroom and office locations

When answering queries:
- Be formal, professional, and helpful
- Provide accurate location information from the datasets
- Format responses in natural, conversational language
- For location queries, format like: "[Location Name] is located in [floor] of [Block Name], which belongs to [Department Name] department"
- If faculty is mentioned, add: "and handled by [Faculty Names]"
- Format floor numbers as: "Ground Floor", "First Floor", "Second Floor", "Third Floor", etc.
- Use complete sentences in a formal, professional tone
- If multiple locations match and they are clearly different, mention all of them
- If a location is not found, politely inform the user"""

            # Create user message with context
            user_message = f"""User Query: {user_query}

Relevant Context from Campus Datasets:
{context}

Please provide a formal, natural language response to the user's query using the context above. 
- Format it as a complete, professional sentence
- For locations: "[Name] is located in [floor] of [Block], which belongs to [Department] department [and handled by faculty names if applicable]"
- Be conversational and formal, not bullet-pointed"""
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",  # You can use gpt-4 for better results
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            print(f"Error calling LLM API: {e}")
            return self._generate_fallback_response(user_query, context_data)
    
    def _generate_clarification_response(self, user_query: str, results: list) -> str:
        """Generate clarification response when multiple matches found for person query"""
        # Group results by department, but only include results that match the person name
        departments = {}
        query_lower = user_query.lower()
        
        # Extract person name from query
        name_parts = [word for word in query_lower.split() 
                     if word not in ['where', 'is', 'mam', 'sir', 'professor', 'prof', 'dr.', 'dr', 'faculty', 'the', 'a', 'an', 'from', 'dept', 'department', 'in', 'of']]
        name_parts = [w for w in name_parts if len(w) > 2]  # Get meaningful words
        search_names = name_parts if name_parts else []
        
        # Filter results to only those matching the person name
        matching_results = []
        for result in results:
            faculty = str(result.get('faculty', '')).lower()
            # Check if any search name appears in faculty name as a complete word
            if search_names:
                matches = False
                for search_name in search_names:
                    if search_name in faculty:
                        # Make sure it's a meaningful match (not substring like "de" in "deisy")
                        faculty_words = faculty.split()
                        if any(search_name in word and len(word) >= len(search_name) for word in faculty_words):
                            matches = True
                            break
                if matches:
                    matching_results.append(result)
            else:
                matching_results.append(result)
        
        # Group by department
        for result in matching_results:
            dept = result.get('department', 'Unknown')
            if dept not in departments:
                departments[dept] = []
            departments[dept].append(result)
        
        # Extract the name being searched for display
        search_name = ' '.join(search_names).strip().capitalize() if search_names else 'this faculty member'
        
        if len(departments) > 1:
            response = f"I found multiple faculty members matching '{search_name}' in different departments. Which one are you looking for?\n\n"
            dept_list = []
            for dept, dept_results in departments.items():
                locations = []
                for r in dept_results:
                    location_name = r.get('name', 'Unknown')
                    floor = r.get('floor', 'Unknown')
                    block = r.get('block', 'Unknown')
                    faculty_info = r.get('faculty', '')
                    # Extract faculty name from faculty_info - only first matching faculty
                    if faculty_info and faculty_info != 'N/A':
                        faculty_str = str(faculty_info).strip()
                        # Handle multiple faculty members - get first one that matches
                        if '\n' in faculty_str:
                            faculty_parts = [f.strip() for f in faculty_str.split('\n') if f.strip()]
                            # Find the one matching our search
                            for f in faculty_parts:
                                if search_names and any(sn in f.lower() for sn in search_names):
                                    faculty_str = f
                                    break
                            if '\n' in faculty_str:
                                faculty_str = faculty_parts[0]  # Fallback to first
                        
                        faculty_clean = faculty_str.replace('Dr.', '').replace('Dr ', '').replace('Mr.', '').replace('Mr ', '').replace('Ms.', '').replace('Ms ', '').replace('Mrs.', '').replace('Mrs ', '').strip()
                        if ', ' in faculty_clean:
                            faculty_clean = faculty_clean.split(',')[0].strip()
                        elif ',' in faculty_clean:
                            faculty_clean = faculty_clean.split(',')[0].strip()
                        
                        # Get meaningful name parts
                        if ' ' in faculty_clean:
                            parts = faculty_clean.split()
                            filtered = [p for p in parts if len(p) > 1]
                            if len(filtered) >= 2:
                                faculty_clean = ' '.join(filtered[-2:])
                            elif filtered:
                                faculty_clean = filtered[-1]
                        
                        # Add title
                        original_lower = faculty_str.lower()
                        if 'mr' in original_lower:
                            faculty_clean += " sir"
                        elif any(t in original_lower for t in ['ms', 'mrs']):
                            faculty_clean += " mam"
                        
                        locations.append(f"{location_name} ({floor} of {block}, handled by {faculty_clean})")
                    else:
                        locations.append(f"{location_name} ({floor} of {block})")
                
                dept_list.append(f"- {dept}: {', '.join(locations)}")
            
            response += "\n".join(dept_list)
            response += "\n\nPlease specify the department you're interested in (e.g., 'from IT department' or 'from CSBS department')."
            return response
        
        # If same department or single result, just show formatted response
        return self._generate_formal_response(user_query, matching_results if matching_results else results)
    
    def _generate_formal_response(self, user_query: str, results: list) -> str:
        """Generate formal, natural language response from results"""
        if not results:
            return "I couldn't find that location in the campus database. Please try rephrasing your query or check if the location name is correct."
        
        query_lower = user_query.lower()
        is_person_query = any(keyword in query_lower for keyword in ['mam', 'sir', 'professor', 'prof', 'dr.', 'dr', 'faculty', 'teacher'])
        
        responses = []
        
        for result in results:
            name = result.get('name', 'Unknown')
            floor = result.get('floor', 'Unknown').lower()
            block = result.get('block', 'Unknown')
            department = result.get('department', 'Unknown')
            faculty = result.get('faculty', '')
            location_type = result.get('type', 'location')
            
                # If it's a person query, format differently
            if is_person_query and faculty and faculty != 'N/A':
                # Extract faculty name and determine gender
                faculty_str = str(faculty).strip()
                query_name_parts = [w for w in query_lower.split() if w not in ['where', 'is', 'mam', 'sir', 'professor', 'prof', 'dr', 'faculty', 'the', 'a', 'an'] and len(w) > 2]
                
                if '\n' in faculty_str or ',' in faculty_str:
                    # Handle multiple faculty members - find the one that matches query
                    if '\n' in faculty_str:
                        faculty_parts = [f.strip() for f in faculty_str.split('\n') if f.strip()]
                    else:
                        # Split by comma
                        faculty_parts = [f.strip() for f in faculty_str.split(',') if f.strip()]
                    
                    matching_faculty = None
                    best_match_score = 0
                    
                    for f in faculty_parts:
                        f_lower = f.lower()
                        match_score = 0
                        # Check how many query name parts match
                        for name_part in query_name_parts:
                            # Use word boundaries for better matching
                            if r'\b' + name_part + r'\b' in f_lower or name_part in f_lower:
                                # Check if it's a meaningful match (not just substring)
                                f_words = f_lower.split()
                                if any(name_part in word and len(word) >= len(name_part) for word in f_words):
                                    match_score += 1
                        
                        if match_score > best_match_score:
                            best_match_score = match_score
                            matching_faculty = f
                    
                    # If no good match found, try fuzzy matching for variations
                    if not matching_faculty or best_match_score == 0:
                        fuzzy_variations = {
                            'yuvashini': ['yuvasini'],
                            'yuvasini': ['yuvashini', 'yuvasini'],
                            'sugantha': ['suganthi', 'sugantha'],
                            'suganthi': ['suganthi', 'sugantha'],
                            'subhashini': ['subhashni', 'subashini'],
                            'subashini': ['subhashni', 'subhashini']
                        }
                        for f in faculty_parts:
                            f_lower = f.lower()
                            for name_part in query_name_parts:
                                if name_part in fuzzy_variations:
                                    for variation in fuzzy_variations[name_part]:
                                        if variation in f_lower:
                                            matching_faculty = f
                                            break
                                    if matching_faculty:
                                        break
                            if matching_faculty:
                                break
                    
                    # Fallback to first faculty if still no match
                    if not matching_faculty and faculty_parts:
                        matching_faculty = faculty_parts[0]
                    
                    faculty_str = matching_faculty if matching_faculty else faculty_str
                
                # Extract and clean faculty name
                faculty_clean = faculty_str.replace('Dr.', '').replace('Dr ', '').replace('Mr.', '').replace('Mr ', '').replace('Ms.', '').replace('Ms ', '').replace('Mrs.', '').replace('Mrs ', '').replace('Professor', '').replace('Prof.', '').replace('Prof ', '').replace('Lab in Charge', '').replace('Member', '').replace('Lab Technician', '').strip()
                
                # Handle commas and parentheses
                if '(' in faculty_clean:
                    faculty_clean = faculty_clean.split('(')[0].strip()
                if ', ' in faculty_clean:
                    faculty_clean = faculty_clean.split(',')[0].strip()
                elif ',' in faculty_clean:
                    faculty_clean = faculty_clean.split(',')[0].strip()
                
                # Get meaningful name parts
                if ' ' in faculty_clean:
                    parts = faculty_clean.split()
                    filtered = [p for p in parts if len(p) > 1]
                    if len(filtered) >= 2:
                        faculty_display = ' '.join(filtered[-2:])
                    elif filtered:
                        faculty_display = filtered[-1]
                    else:
                        faculty_display = parts[-1] if parts else faculty_clean
                else:
                    faculty_display = faculty_clean
                
                # Determine gender and pronoun - prioritize query clues, then faculty title
                original_lower = faculty_str.lower()
                query_lower_check = user_query.lower()
                
                # Check query for gender clues first (mam/sir in query) - this is most reliable
                if 'mam' in query_lower_check:
                    pronoun = "She"
                    possessive = "her"
                    title = "mam"
                elif 'sir' in query_lower_check:
                    pronoun = "He"
                    possessive = "his"
                    title = "sir"
                # Otherwise check faculty title from data
                elif 'mr' in original_lower or 'mr.' in original_lower or 'mr ' in original_lower:
                    pronoun = "He"
                    possessive = "his"
                    title = "sir"
                elif any(title_word in original_lower for title_word in ['ms', 'ms.', 'mrs', 'mrs.', 'miss']):
                    pronoun = "She"
                    possessive = "her"
                    title = "mam"
                else:
                    # Default based on query if available
                    if 'mam' in query_lower_check:
                        pronoun = "She"
                        possessive = "her"
                        title = "mam"
                    elif 'sir' in query_lower_check:
                        pronoun = "He"
                        possessive = "his"
                        title = "sir"
                    else:
                        pronoun = "He/She"
                        possessive = "his/her"
                        title = ""
                
                # Build formal person-focused response (no "handled by" at end, no He/She prefix)
                if title:
                    response = f"{faculty_display} {title} is a faculty member of the {department} department, and {possessive} place is at {name} located in the {floor} of {block}."
                else:
                    response = f"{faculty_display} is a faculty member of the {department} department, and {possessive} place is at {name} located in the {floor} of {block}."
            else:
                # Build the response sentence for location queries
                if location_type == 'lab':
                    response = f"{name} is located in the {floor} of {block}, which belongs to the {department} department"
                elif location_type == 'classroom':
                    response = f"{name} classroom is located in the {floor} of {block}, which belongs to the {department} department"
                elif location_type == 'staffroom':
                    response = f"{name} is located in the {floor} of {block}, which belongs to the {department} department"
                else:
                    response = f"{name} is located in the {floor} of {block}, which belongs to the {department} department"
            
            # Add faculty information if available - ONLY for location queries, NOT person queries
            if faculty and faculty != 'N/A' and pd.notna(faculty) and not is_person_query:
                # Clean up faculty names - remove titles and format nicely
                faculty_str = str(faculty).strip()
                if '\n' in faculty_str:
                    # Multiple faculty members
                    faculty_list = [f.strip() for f in faculty_str.split('\n') if f.strip()]
                    faculty_names = []
                    for f in faculty_list:
                        # Extract just the name without common titles
                        name_clean = f.replace('Dr.', '').replace('Dr ', '').replace('Mr.', '').replace('Mr ', '').replace('Ms.', '').replace('Ms ', '').replace('Mrs.', '').replace('Mrs ', '').replace('Professor', '').replace('Prof.', '').replace('Prof ', '').replace('Lab in Charge', '').replace('Member', '').replace('Lab Technician', '').strip()
                        # Remove extra parentheses and content
                        if '(' in name_clean:
                            name_clean = name_clean.split('(')[0].strip()
                        # Get surname (last name)
                        if ', ' in name_clean:
                            name_clean = name_clean.split(',')[0].strip()
                        elif ',' in name_clean:
                            name_clean = name_clean.split(',')[0].strip()
                        
                        if ' ' in name_clean:
                            parts = name_clean.split()
                            # Skip single letter initials (like "M.", "K.")
                            filtered_parts = [p for p in parts if len(p) > 1 or not p.endswith('.')]
                            
                            if len(filtered_parts) >= 2:
                                # Take last two meaningful parts (e.g., "Kavitha Devi")
                                name_clean = ' '.join(filtered_parts[-2:])
                            elif len(filtered_parts) == 1:
                                name_clean = filtered_parts[0]
                            else:
                                # Fallback: take last part
                                name_clean = parts[-1] if parts else name_clean
                        
                        if name_clean and len(name_clean) > 2:
                            # Add "sir" or "mam" based on title
                            original_lower = f.lower()
                            if 'mr' in original_lower:
                                faculty_names.append(f"{name_clean} sir")
                            elif any(title in original_lower for title in ['ms', 'mrs']):
                                faculty_names.append(f"{name_clean} mam")
                            else:
                                faculty_names.append(name_clean)
                    
                    if faculty_names:
                        names_str = ' and '.join(faculty_names)
                        response += f" and is handled by {names_str}"
                else:
                    # Single faculty member
                    name_clean = faculty_str.replace('Dr.', '').replace('Dr ', '').replace('Mr.', '').replace('Mr ', '').replace('Ms.', '').replace('Ms ', '').replace('Mrs.', '').replace('Mrs ', '').replace('Professor', '').replace('Prof.', '').replace('Prof ', '').replace('Lab in Charge', '').replace('Member', '').replace('Lab Technician', '').strip()
                    # Remove extra parentheses
                    if '(' in name_clean:
                        name_clean = name_clean.split('(')[0].strip()
                    if ', ' in name_clean:
                        name_clean = name_clean.split(',')[0].strip()
                    elif ',' in name_clean:
                        name_clean = name_clean.split(',')[0].strip()
                    
                    # Get the surname (last name) - handle cases like "M. K. Kavitha Devi"
                    if ' ' in name_clean:
                        parts = name_clean.split()
                        # Skip single letter initials (like "M.", "K.")
                        filtered_parts = [p for p in parts if len(p) > 1 or not (p.endswith('.') or len(p) == 1)]
                        
                        if len(filtered_parts) >= 2:
                            # Take last two meaningful parts (e.g., "Kavitha Devi" from "M. K. Kavitha Devi")
                            name_clean = ' '.join(filtered_parts[-2:])
                        elif len(filtered_parts) == 1:
                            name_clean = filtered_parts[0]
                        elif parts:
                            # Fallback: take last non-initial part
                            for p in reversed(parts):
                                if len(p) > 1:
                                    name_clean = p
                                    break
                            else:
                                name_clean = parts[-1]
                        else:
                            name_clean = name_clean
                    
                    # Check if we have a meaningful name
                    if name_clean and len(name_clean) > 2:
                        # Add appropriate title
                        original_lower = faculty_str.lower()
                        if 'mr' in original_lower or 'mr.' in original_lower:
                            response += f" and is handled by {name_clean} sir"
                        elif any(title in original_lower for title in ['ms', 'ms.', 'mrs', 'mrs.']):
                            response += f" and is handled by {name_clean} mam"
                        elif 'dr' in original_lower:
                            # For Dr., check if it's a female name (Ms/Mrs) or default
                            if any(title in original_lower for title in ['ms', 'mrs']):
                                response += f" and is handled by {name_clean} mam"
                            else:
                                response += f" and is handled by {name_clean}"
                        else:
                            response += f" and is handled by {name_clean}"
            
            responses.append(response + ".")
        
        # If multiple results, combine them naturally
        if len(responses) == 1:
            return responses[0]
        elif len(responses) == 2:
            return f"{responses[0]}\n\nAdditionally, {responses[1]}"
        else:
            # For multiple results, format nicely
            return "\n\n".join([f"{i+1}. {r}" for i, r in enumerate(responses)])
    
    def _generate_fallback_response(self, user_query: str, context_data: dict) -> str:
        """Fallback response generator when LLM API is not available"""
        context = context_data.get('context', '')
        results = context_data.get('results', [])
        needs_clarification = context_data.get('needs_clarification', False)
        is_person_query = context_data.get('is_person_query', False)
        
        # Handle clarification needed
        if needs_clarification and is_person_query and len(results) > 1:
            return self._generate_clarification_response(user_query, results)
        
        if "not found" in context.lower() or not context.strip() or not results:
            return "I couldn't find that location in the campus database. Please try rephrasing your query or check if the location name is correct."
        
        # Use the formal response generator
        return self._generate_formal_response(user_query, results)
