import pdfplumber
import spacy
import re
from collections import Counter
from spacy.matcher import Matcher
import logging
from sys import argv

'''
Goals:
Personal info: Name, CC
Amount: search for $usd within dispute keyword
Legitimacy Proofs: Search for common phrases associated with ID, payment, and delivery verification
'''


class PDFParser:
    def __init__(self, nlp_model="en_core_web_sm"):
        # Load the SpaCy NLP model
        self.nlp = spacy.load(nlp_model)

    def search_by_pattern(self, text, patterns, fn=lambda x: {x.text}):
        # Initialize the matcher
        matcher = Matcher(self.nlp.vocab)

        # Define the pattern for matching
        matcher.add("Pattern", patterns)

        # Process the text with SpaCy
        doc = self.nlp(text)

        # Search for the pattern in the text
        matches = matcher(doc)
        matched_results = set()
        for _, start, end in matches:
            matched_span = doc[start:end]
            # apply follow-up pattern match function
            matched_results |= fn(matched_span)

        return list(matched_results) if matched_results else None

    # Follow-up pattern matching methods ========================

    @staticmethod
    def cc_fn(matched_span):
        retval = set()
        for token in matched_span:
            if token.like_num and len(token.text) == 4:
                retval.add(token.text.strip())
        return retval

    @staticmethod
    def reason_fn(matched_span):
        # Get the sentence containing the match
        sentence = matched_span.sent.text.strip()

        # Get the sentence before (if available)
        doc = matched_span.doc
        sent_start = matched_span.sent.start
        if sent_start > 0:
            prev_sent = doc[doc[sent_start -
                                1].sent.start:doc[sent_start - 1].sent.end].text.strip()
            if len(prev_sent) > 10:  # Only include if it's a substantial sentence
                return {f"{prev_sent} {sentence}"}

        return {sentence}

    # ===========================================================

    def parse_pdf(self, file):
        # Read from PDF and convert to raw text
        try:
            with pdfplumber.open(file) as pdf:
                text = " ".join(page.extract_text()
                                or "" for page in pdf.pages)
        except Exception as e:
            print("Error: Something went wrong reading the file.")
            return {}
        text = text.replace("\n", " ")

        # Set up variables
        results = {}
        results['user_info'] = {}

        doc = self.nlp(text)
        user_info = Counter()
        amount = -1

        # Pull basic customer information from doc
        for ent in doc.ents:
            logging.info(
                f"DEBUG: Entity found - Text: {ent.text}, Label: {ent.label_}")
            if ent.label_ == "PERSON" and not ent.text.isnumeric():  # Assuming user info is a person
                user_info[ent.text] += 1
            elif ent.label_ == 'MONEY':
                start_pos = ent.start_char
                if start_pos > 0 and text[start_pos - 1] == "$":
                    print("Updating amount")
                    print(re.sub(r'\D+$', '', ent.text))
                    amount = max(amount, float(re.sub(r'\D+$', '', ent.text)))

        if amount is None and "$" in text:  # Use the backup search for amount if None
            amount = self.search_amount(text)
            print("Backup amount method used")

        results['user_info']['name'] = user_info.most_common(1)[0][0]
        results['amount'] = amount

        # Parse more detailed results

        results['user_info']['credit_card'] = list(self.search_by_pattern(text, [[
            {"LOWER": "ending"},
            {"LOWER": "in"},
            {"IS_DIGIT": True, "LENGTH": 4}
        ]], self.cc_fn))[0]

        # Find legitimacy proofs and categorize them
        legitimacy_evidence = {
            "identity_verification": [],
            "delivery_confirmation": [],
            "payment_verification": [],
        }

        # Identity verification evidence
        id_verification = self.search_by_pattern(text, [
            [{"LOWER": {"IN": ["verify", "verification", "avs", "address",
                               "authorized", "tokenized", "logging", "authentication"]}}],
            [{"LOWER": "ip"}, {"LOWER": "address"}],
            [{"LOWER": "tracking"}],
            [{"LOWER": "billing"}, {"LOWER": "address"}],
            [{"LOWER": "shipping"}, {"LOWER": "address"}],
            [{"LOWER": "logged"}, {"LOWER": "in"}],
            [{"LOWER": "satisfied"}, {"OP": "*"}, {"LOWER": "checks"}],
            [{"LOWER": "pass"}]
        ], self.reason_fn)
        if id_verification:
            legitimacy_evidence["identity_verification"] = id_verification

        # Delivery confirmation evidence
        delivery_confirmation = self.search_by_pattern(text, [
            [{"LOWER": "deliver"}],
            [{"LOWER": "delivered"}, {"LOWER": "to"}],
            [{"LOWER": "shipped"}],
            [{"LOWER": "tracking"}, {"LOWER": "number"}],
            [{"LOWER": "package"}],
            [{"LOWER": "arrival"}],
            [{"LOWER": "received"}],
            [{"LOWER": "fulfilled"}]
        ], self.reason_fn)
        if delivery_confirmation:
            legitimacy_evidence["delivery_confirmation"] = delivery_confirmation

        # Payment verification evidence
        payment_verification = self.search_by_pattern(text, [
            [{"LOWER": "charge"}, {"OP": "*"}, {"LOWER": "valid"}],
            [{"LOWER": "billed"}],
            [{"LOWER": "authorization"}],
            [{"LOWER": "charged"}],
            [{"LOWER": "payment"}, {"LOWER": "method"}],
            [{"LOWER": "order"}, {"LOWER": "summary"}],
            [{"LOWER": "ending"}, {"LOWER": "in"}],
            [{"LOWER": "recurring"}]
        ], self.reason_fn)
        if payment_verification:
            legitimacy_evidence["payment_verification"] = payment_verification

        results['legitimacy_evidence'] = legitimacy_evidence
        return results

    # BACKUP METHODS ============================================

    @staticmethod
    def search_amount(text):
        words = text.split()
        for word in words:
            if '$' in word:
                return word
        return ""


if __name__ == "__main__":
    parser = PDFParser()
    parser.parse_pdf(argv[1])
