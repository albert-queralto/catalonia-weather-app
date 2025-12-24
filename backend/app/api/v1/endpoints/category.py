from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_session
from app.db.models.category import Category

router = APIRouter()

@router.get("/categories", response_model=list[str])
def list_categories(db: Session = Depends(get_session)):
    """
    Retrieve all category names.

    Returns:
        List of category names.
    """
    categories = db.query(Category).all()
    return [c.name for c in categories]

@router.post("/categories", response_model=str)
def create_category(name: str, db: Session = Depends(get_session)):
    """
    Create a new category.

    Args:
        name (str): The name of the new category.

    Returns:
        The name of the created category.

    Raises:
        HTTPException: If the category already exists.
    """
    if db.query(Category).filter_by(name=name).first():
        raise HTTPException(status_code=400, detail="Category already exists")
    category = Category(name=name)
    db.add(category)
    db.commit()
    return category.name

@router.put("/categories/{old_name}", response_model=str)
def update_category(old_name: str, new_name: str, db: Session = Depends(get_session)):
    """
    Update the name of an existing category.

    Args:
        old_name (str): The current name of the category.
        new_name (str): The new name for the category.

    Returns:
        The updated category name.

    Raises:
        HTTPException: If the category does not exist or the new name already exists.
    """
    category = db.query(Category).filter_by(name=old_name).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    if db.query(Category).filter_by(name=new_name).first():
        raise HTTPException(status_code=400, detail="New category name already exists")
    category.name = new_name
    db.commit()
    return category.name

@router.delete("/categories/{name}", response_model=dict)
def delete_category(name: str, db: Session = Depends(get_session)):
    """
    Delete a category by name.

    Args:
        name (str): The name of the category to delete.

    Returns:
        A message indicating the category was deleted.

    Raises:
        HTTPException: If the category does not exist.
    """
    category = db.query(Category).filter_by(name=name).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    db.delete(category)
    db.commit()
    return {"detail": "Category deleted"}