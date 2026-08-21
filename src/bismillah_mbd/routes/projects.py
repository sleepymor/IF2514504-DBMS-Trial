from fastapi import APIRouter

router = APIRouter(
    prefix="/projects",
    tags=["Projects"],
)

@router.get("/")
def get_project():
    return{"get project"}

@router.get("/{project_id}")
def get_project(project_id: int):
    return{"get project", project_id}

@router.post("/")
def create_project():
    return{"create project"}

@router.put("/{project_id}")
def update_project(project_id: int):
    return{"update project", project_id}

@router.delete("/{project_id}")
def delete_project(project_id: int):
    return{"delete project", project_id}