import pdfplumber
import sys
import spacy
import string
import re
from collections import Counter
from spacy.tokenizer import Tokenizer
from spacy.matcher import Matcher
from spacy.symbols import ORTH
'''
Goal Info:
Personal info: Name, CC
Amount: search for $usd within dispute keyword
Reason: return a reason for that chargeback/dispute/failure
legitimacy: chargback companies proof of legitimacy (IP login, proof of purchase/service used, etc)
'''
nlp = spacy.load("en_core_web_sm")

def search_by_pattern(text,patterns, fn=lambda x:set()):    
    # Initialize the matcher
    matcher = Matcher(nlp.vocab)
    
    # Define the pattern for matching
    matcher.add("Pattern", patterns)
    
    # Process the text with SpaCy
    doc = nlp(text)
    
    # Search for the pattern in the text
    matches = matcher(doc)
    matched_results = set()
    for _, start, end in matches:
        matched_span = doc[start:end]
        matched_results |= fn(matched_span) # apply follow up pattern match function
        
    return list(matched_results) if matched_results else None


# follow up pattern matching methods ========================

def cc_fn(matched_span):
    retval = set()
    for token in matched_span:
            if token.like_num and len(token.text) == 4:
                retval.add( token.text.strip())
    return retval

def reason_fn(matched_span):
    return {matched_span.sent.text.strip()}

# ===========================================================

def parse_pdf(file):
    try:
        with pdfplumber.open(file) as pdf:
            text = ""
            for page in pdf.pages:
                text +=  " " + page.extract_text() or ""
    except Exception as e:
        print("Error: Something wen wrong reading the file.")
        return {}
    text = text.replace("\n", " ")

    results = {}

    doc = nlp(text)
    user_info = Counter()
    amount = -1

    # pull basic customer information from doc
    for ent in doc.ents:
        print(f"DEBUG: Entity found - Text: {ent.text}, Label: {ent.label_}")
        if ent.label_ == "PERSON" and not ent.text.isnumeric():  # Assuming user info is a person
            user_info[ent.text] +=1
        elif ent.label_ == 'MONEY':
            start_pos = ent.start_char
            if start_pos > 0 and text[start_pos - 1] == "$":
                print("updating amount")
                print(re.sub(r'\D+$', '', ent.text))
                amount = max(amount, float(re.sub(r'\D+$', '', ent.text)))

    if amount is None and "$" in text: # use the backup search for amount
        amount = search_amount(text)
        print("backup amount method used")
    
    results['user_info'] = user_info.most_common(1)[0][0]
    results['amount'] = amount
    
    # parse more detailed results

    results['credit_card'] = list(search_by_pattern(text,[[
            {"LOWER": "ending"}, 
            {"LOWER": "in"}, 
            {"IS_DIGIT": True, "LENGTH": 4}
        ]],cc_fn))[0]
    results['reason'] = search_by_pattern(text,[
            [{"LOWER": "because"}],  # Look for explicit reasons
            [{"LOWER": "reason"}, {"LOWER": "for"}],  # "reason for"
            [{"LOWER": "proof"}, {"LOWER": "of"}],  # "proof of"
            [{"LOWER": "transaction"}],  # Transaction mentions

            [{"LOWER": "receipt"}],  # Receipt mentions
            [{"LOWER": "evidence"}],  # Evidence mentions
            [{"LOWER": "used"}, {"LOWER": "for"}],  # "used for"
            [{"LOWER": "access"}],  # "used for"
            [{"LOWER": "deliver"}]
        ],reason_fn)
    results['resolve'] = search_by_pattern(text,[        [{"LOWER": "resolve"}]  # resolution mentions
        ],reason_fn)
    return results
    
# BACKUP FUNCTIONS ===============================

def search_amount(text):
    words = text.split()
    for word in words:
        if '$' in word:
            return word
    return ""

if __name__ == "__main__":
    parse_pdf(sys.argv[1])