from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from starlette.responses import JSONResponse
from starlette.requests import Request
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import BaseModel, EmailStr
from typing import List
from tortoise.contrib.fastapi import register_tortoise
from models import (supplier_pydantic, supplier_pydanticIn, Supplier, product_pydanticIn, product_pydantic, Product)
from dotenv import dotenv_values
from fastapi.middleware.cors import CORSMiddleware

credentials = dotenv_values(".env")

print(credentials)


app = FastAPI()

# adding cors urls
origins = [
    'http://localhost:3000'
]

# add middleware
app.add_middleware(
    CORSMiddleware, 
    allow_origins = origins, 
    allow_credentials=True,
    allow_methods =["*"],
    allow_headers = ["*"]
)


##### HOME #####
@app.get('/')
def index():
    return {"Msg": "Go to /docs for the API documentation"}


##### SUPPLIER CRUD #####
@app.post('/supplier')
async def add_supplier(supplier_info: supplier_pydanticIn):
    supplier_obj = await Supplier.create(**supplier_info.dict(exclude_unset=True))
    response = await supplier_pydantic.from_tortoise_orm(supplier_obj)
    return {"status": "ok", "data": response}

@app.get('/supplier')
async def get_all_suppliers():
    response = await supplier_pydantic.from_queryset(Supplier.all())
    return {"status": "ok", "data": response}

@app.get('/supplier/{supplier_id}')
async def get_specific_supplier(supplier_id: int):
    response = await supplier_pydantic.from_queryset_single(Supplier.get(id=supplier_id))
    return {"status": "ok", "data": response}

@app.put('/supplier/{supplier_id}')
async def update_supplier(supplier_id: int, update_info: supplier_pydanticIn):
    supplier = await Supplier.get(id = supplier_id)
    update_info = update_info.dict(exclude_unset=True)
    supplier.name = update_info['name']
    supplier.company = update_info['company']
    supplier.phone = update_info['phone']
    supplier.email = update_info['email']
    await supplier.save()
    response = await supplier_pydantic.from_tortoise_orm(supplier)
    return {"status": "ok", "data": response}

@app.delete('/supplier/{supplier_id}')
async def delete_supplier(supplier_id: int):
    deleted_supplier = await Supplier.filter(id=supplier_id).delete()
    if not deleted_supplier:
        raise HTTPException(status_code=404, detail=f"Supplier {supplier_id} not found")
    return {"status": "ok"}


##### PRODUCT CRUD #####
@app.post('/product/{supplier_id}')
async def add_product(supplier_id: int, product_details: product_pydanticIn):
    supplier = await Supplier.get(id=supplier_id)
    product_details = product_details.dict(exclude_unset=True)
    product_details['revenue'] += product_details['quantity_sold'] * product_details['unit_price']
    product_obj = await Product.create(**product_details, supplied_by = supplier)
    response = await product_pydantic.from_tortoise_orm(product_obj)
    return {"status": "ok", "data": response}

@app.get("/product")
async def all_products():
    response = await product_pydantic.from_queryset(Product.all())
    return {"status": "ok", "data": response}

@app.get("/product/{id}")
async def spectific_product(id: int):
    response = await product_pydantic.from_queryset_single(Product.get(id = id))
    return {"status": "ok", "data": response}

@app.put('/product/{id}')
async def update_product(id: int, update_info: product_pydanticIn):
    product = await Product.get(id=id)
    update_info = update_info.dict(exclude_unset=True)
    product.name = update_info['name']
    product.quantity_in_stock = update_info['quantity_in_stock']
    product.revenue += (update_info['quantity_sold'] * update_info["unit_price"]) + update_info['revenue']
    product.quantity_sold += update_info['quantity_sold']
    product.unit_price = update_info['unit_price']
    await product.save()
    response = await product_pydantic.from_tortoise_orm(product)
    return {"status": "ok", "data": response}

@app.delete('/product/{id}')
async def delete_product(id: int):
    deleted_product = await Product.filter(id=id).delete()
    if not deleted_product:
        raise HTTPException(status_code=404, detail=f"Product {id} not found")
    return {"status": "ok"}

class EmailSchema(BaseModel):
    email: List[EmailStr]

class EmailContent(BaseModel):
    message: str
    subject: str



conf = ConnectionConfig(
    MAIL_USERNAME = credentials["EMAIL"],
    MAIL_PASSWORD = credentials["PASSWORD"],
    MAIL_FROM = credentials["EMAIL"],
    MAIL_PORT = 587,
    MAIL_SERVER = "smtp.gmail.com",
    MAIL_FROM_NAME="fastapiReact",
    MAIL_TLS = True,
    MAIL_SSL = False,
    USE_CREDENTIALS = True
)



@app.post('/email/{product_id}')
async def send_email(product_id: int, content: EmailContent):
    product = await Product.get(id=product_id)
    supplier = await product.supplied_by
    supplier_email = [supplier.email]

    html = f"""
    <h5>John D. Industries</h5>
    <br>
    <p>{content.message}</p>
    <br>
    <h6>Best Regards,</h6>
    <h6>John D.</h6>
    """

    message = MessageSchema(
        subject=content.subject,
        recipients=supplier_email,  # List of recipients, as many as you can pass 
        body=html,
        subtype="html"
    )

    fm = FastMail(conf)
    await fm.send_message(message)
    return {"status": "ok"}

        




#### DB SET-UP #####
register_tortoise(
    app, 
    db_url="sqlite://database.sqlite3", 
    modules={"models": ["models"]}, 
    generate_schemas=True, 
    add_exception_handlers=True
)
