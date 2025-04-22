import pdfplumber
import sys
import spacy
import re
from collections import Counter
from spacy.matcher import Matcher
import logging
'''
Goal Info:
Personal info: Name, CC
Amount: search for $usd within dispute keyword
Reason: return a reason for that chargeback/dispute/failure
resolve: look to see if the company has tried to resolve the issue or give instructions to resolve the issue
'''
nlp = spacy.load("en_core_web_sm")


def search_by_pattern(text, patterns, fn=lambda x: {x.text}):
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
        # apply follow up pattern match function
        matched_results |= fn(matched_span)

    return list(matched_results) if matched_results else None


# follow up pattern matching methods ========================

def cc_fn(matched_span):
    retval = set()
    for token in matched_span:
        if token.like_num and len(token.text) == 4:
            retval.add(token.text.strip())
    return retval


def reason_fn(matched_span):
    # Get the sentence containing the match
    sentence = matched_span.sent.text.strip()
    
    # Get the sentence before (if available)
    doc = matched_span.doc
    sent_start = matched_span.sent.start
    if sent_start > 0:
        prev_sent = doc[doc[sent_start-1].sent.start:doc[sent_start-1].sent.end].text.strip()
        if len(prev_sent) > 10:  # Only include if it's a substantial sentence
            return {f"{prev_sent} {sentence}"}
    
    return {sentence}

# ===========================================================


def parse_pdf(file):
    try:
        with pdfplumber.open(file) as pdf:
            text = ""
            for page in pdf.pages:
                text += " " + page.extract_text() or ""
    except Exception as e:
        print("Error: Something went wrong reading the file.")
        return {}
    text = text.replace("\n", " ")

    results = {}
    results['user_info'] = {}

    doc = nlp(text)
    user_info = Counter()
    amount = -1

    # pull basic customer information from doc
    for ent in doc.ents:
        logging.info(
            f"DEBUG: Entity found - Text: {ent.text}, Label: {ent.label_}")
        if ent.label_ == "PERSON" and not ent.text.isnumeric():  # Assuming user info is a person
            user_info[ent.text] += 1
        elif ent.label_ == 'MONEY':
            start_pos = ent.start_char
            if start_pos > 0 and text[start_pos - 1] == "$":
                print("updating amount")
                print(re.sub(r'\D+$', '', ent.text))
                amount = max(amount, float(re.sub(r'\D+$', '', ent.text)))

    if amount is None and "$" in text:  # use the backup search for amount if None
        amount = search_amount(text)
        print("backup amount method used")

    results['user_info']['name'] = user_info.most_common(1)[0][0]
    results['amount'] = amount

    # parse more detailed results

    results['user_info']['credit_card'] = list(search_by_pattern(text, [[
        {"LOWER": "ending"},
        {"LOWER": "in"},
        {"IS_DIGIT": True, "LENGTH": 4}
    ]], cc_fn))[0]

    
    # Find legitimacy proofs and categorize them
    legitimacy_evidence = {
        "identity_verification": [],
        "delivery_confirmation": [],
        "payment_verification": [],
    }
    
    # Identity verification evidence
    id_verification = search_by_pattern(text, [
        [{"LOWER": {"IN": ["verify", "verification", "avs", "address", "authorized", "tokenized", "logging", "authentication"]}}],
        [{"LOWER": "ip"}, {"LOWER": "address"}],
        [{"LOWER": "tracking"}],
        [{"LOWER": "billing"}, {"LOWER": "address"}],
        [{"LOWER": "shipping"}, {"LOWER": "address"}],
        [{"LOWER": "logged"}, {"LOWER": "in"}],
        [{"LOWER": "satisfied"}, {"OP": "*"}, {"LOWER": "checks"}],
        [{"LOWER": "pass"}]
    ], reason_fn)
    if id_verification:
        legitimacy_evidence["identity_verification"] = id_verification
    
    # Delivery confirmation evidence
# Delivery confirmation evidence
    delivery_confirmation = search_by_pattern(text, [
        [{"LOWER": "deliver"}],
        [{"LOWER": "delivered"}, {"LOWER": "to"}],
        [{"LOWER": "shipped"}],
        [{"LOWER": "tracking"}, {"LOWER": "number"}],
        [{"LOWER": "package"}],
        [{"LOWER": "arrival"}],
        [{"LOWER": "received"}],
        [{"LOWER": "fulfilled"}]
    ], reason_fn)
    if delivery_confirmation:
        legitimacy_evidence["delivery_confirmation"] = delivery_confirmation
    
    # Payment verification evidence
    payment_verification = search_by_pattern(text, [
        [{"LOWER": "charge"}, {"OP": "*"}, {"LOWER": "valid"}],
        [{"LOWER": "billed"}],
        [{"LOWER": "authorization"}],
        [{"LOWER": "charged"}],
        [{"LOWER": "payment"}, {"LOWER": "method"}],
        [{"LOWER": "order"}, {"LOWER": "summary"}],
        [{"LOWER": "ending"}, {"LOWER": "in"}],
        [{"LOWER": "recurring"}]
    ], reason_fn)
    if payment_verification:
        legitimacy_evidence["payment_verification"] = payment_verification
    results['legitimacy_evidence'] = legitimacy_evidence
    # results['resolve'] = search_by_pattern(text, [[{"LOWER": "resolve"}]  # resolution mentions
    #                                               ], reason_fn)
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
