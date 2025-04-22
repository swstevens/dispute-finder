
# Dispute Parser

This is a take home project which processes a given pdf file into more manageable json formatting. The goal of this application is to glean important information like user info, transaction info, and reasons for the chargeback dispute. This was completed on a relatively short time frame, so sections may be rudimentary, but are fully functional.

## Thought Process

While working through this problem there were a few tiers to which I made progress. The first of which was undesrtanding the steps of the backend functionality. I broke the problem into these steps first:

- parsing the pdf file into usable text
- search the text for relevant/key information 
- converting this information into a transmittable format

This approach made building out each step relatively easy. For the first I opted to use pdfplumber to convert the pdf text into a more manageable data stream. This implementation only does text, but could be expanded to cover images if warranted. The second step required a little more research. In the past, I've done projects where you can feed a pdf into an LLM to get a summarization of the pdf, but a generic NLP served to be a better tool. I opted to use another python library, spaCy, to accomplish this. The final step of converting the information into transmittable format was easy, simply casting the dictionary return value to a JSON response made consuming it on the front end straightforward.

Another aspect of the problem was which parts of the . I opted for a few pieces of identifying information of the customer (specifically name and last 4 cc), as well as trying my hand at parsing the proof of legitimacy sections for key sentences regarding the chargeback. This way, you have an approach for each important aspect of a chargeback that can be improved and iterated on as the app progresses. 

The frontend is a simple html page with allows the user to upload a pdf, submit it to the backend, and show the json response on screen after it is received back from the fastapi backend.

### Key Functions

#### parse_pdf

The main method for the module. It has a 4 main parts. Parsing the pdf into raw text, a generic keyword search block, and a more refined phrase search block.  Because this was a shorter assignment, I decided to leave both implementations in the function. In theory, you'd want everything to use the `search_by_pattern` function rather than the generic keyword search function. Searching for important keywords using the ent labels provides better granularity for specific terms like user info, while the pattern searching helps to find important phrases within sentences for the legitimacy proofs. 

#### search_by_pattern

I want to also go over the `search_by_pattern` function, which takes in the raw text, a search pattern, and a sub-helper function for further finetuning of the response. Using the search pattern with spaCy, it finds the matches in the text. Then, using the sub-helper function, further cleans the matches into either single words, phrases, or full sentences. This was used with a variety of common phrases as patterns for a few types of common chargeback representment types: identitty verification (in cases of fraud, etc), delivery confirmation (to confirm that services were rendered or received), and payment verification (to confirm the payment event). These three events serve as an example that can be further honed for more specific categories.
## API Reference

#### Get 
```http
  GET /
```
Returns the homepage of the application, a simple upload page which will show the json information on response.

#### Upload

```http
  POST /Upload
```

| Parameter | Type     | Description                       |
| :-------- | :------- | :-------------------------------- |
| `file`      | `pdf` | **Required**. A file must be uploaded to be parsed. |

#### parse(file)

Accepts a file, parsing the data using NLP, and returns a json formatted as below. User info and legitimacy_evidence are grouped for ease of use.


```
{
  "user_info": {
    "name": "Mary Sellers",
    "credit_card": "2345"
  },
  "amount": 26.39,
  "legitimacy_evidence": {
    "identity_verification": [
      "The charge has a statement descriptor of Peloton Inc. Customer Activity and Access Logs Our system automatically logs customers via their IP address, to make a record of the actions they take in our system and to provide an added level of verification when processing orders."
    ],
    "delivery_confirmation": [
      "We fulfill customer orders directly, and correspond repeatedly with our customers to make sure they have accurate billing, purchase, subscription and cancellation information. Summary On 2024-03-01, Peloton received notice that our customer Mary Sellers, filed a dispute for a charge we made in the amount of $26.39."
    ],
    "payment_verification": [
      "The charge was for the amount of $26.39 billed to a Mastercard ending in 2345. The charge has a statement descriptor of Peloton Inc."
    ]
  }
}
```
## Deployment

To deploy this project run the following commands:

```bash
  python3 -m venv disputefinder
  pip install -r requirements.txt
  uvicorn app.main:app --reload
  python3 -m spacy download en_core_web_sm
  
```

![alt text](Isolated.png "Title")
## Feedback

This was a lot of fun! I've been wanting to more heavily use NLP, and this was the perfect opportunity to do so. If there are any corrections you'd like me to make before the deadline, there are issues with testing, or this doesn't quite hit the mark in terms of your requirements, please let me know and I can make some further changes! 
