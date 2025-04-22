from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging
import os
from io import BytesIO
from app.parser import PDFParser


app = FastAPI()

# set up html files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    # Allows all origins, you can specify specific origins here like ["http://localhost:3000"]
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    # Path to your index.html file
    index_file_path = os.path.join("static", "index.html")

    # Read the index.html file and return as a response
    try:
        with open(index_file_path, "r") as file:
            content = file.read()
        return HTMLResponse(content=content)
    except FileNotFoundError:
        logging.error("Index file not found.")
        raise HTTPException(status_code=404, detail="Index file not found.")


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        logging.warning("Uploaded file is not a PDF.")
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    try:
        file_content = await file.read()
        pdf_file = BytesIO(file_content)

        parser = PDFParser()
        result = parser.parse_pdf(pdf_file)

        if not result:
            raise ValueError("Failed to parse PDF content.")

        return JSONResponse(content=result)
    except ValueError as ve:
        logging.error(f"Parsing error: {ve}")
        raise HTTPException(status_code=422, detail="Invalid PDF content.")
    except Exception as e:
        logging.exception("Unexpected error occurred.")
        raise HTTPException(status_code=500, detail="Internal server error.")

