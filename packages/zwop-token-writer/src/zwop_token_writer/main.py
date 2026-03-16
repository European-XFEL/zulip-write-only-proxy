from fastapi import FastAPI
from zwop_contracts import FileWriteRequest, FileWriteSummary

app = FastAPI(title="zwop-token-writer")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/write", response_model=FileWriteSummary)
async def write_file(request: FileWriteRequest) -> FileWriteSummary:
    return FileWriteSummary(
        proposal=request.proposal_no,
        results=[],
        status_code=501,
    )


def run() -> None:
    import uvicorn

    uvicorn.run("zwop_token_writer.main:app", host="0.0.0.0", port=8443)
