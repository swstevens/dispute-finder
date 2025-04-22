from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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
    with open(index_file_path, "r") as file:
        content = file.read()

    return HTMLResponse(content=content)


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # Process the file (e.g., save it, parse it, etc.)
    # For example, just return the file name and content type in the response
    file_content = await file.read()

    # Convert the file content into a BytesIO object to be used by pdfplumber
    pdf_file = BytesIO(file_content)
    plumber = PDFParser()
    print(plumber.parse_pdf(pdf_file))
    return JSONResponse(content=plumber.parse_pdf(pdf_file))
