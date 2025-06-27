from mongoengine import Document, StringField, IntField, ReferenceField, BooleanField
from mongoengine import EmbeddedDocument, EmbeddedDocumentField, ListField

class User(Document):
    email = StringField(required=True, unique=True)
    password = StringField(required=True)
    is_admin = BooleanField(default=False)

class Book(Document):
    iban = StringField(required=True, unique=True)
    name = StringField(required=True)
    author = StringField(required=True)
    price = IntField(required=True)
    quantity = IntField(required=True)
    image = StringField()  

class Cart(Document):
    user = ReferenceField(User, required=True)
    book = ReferenceField(Book, required=True)
    quantity = IntField(default=1, required=True)

class PurchasedBook(EmbeddedDocument):
    name = StringField(required=True)
    price = IntField(required=True)
    quantity = IntField(required=True)

class Shipping(Document):
    user = ReferenceField(User, required=True)
    name = StringField(required=True)
    address = StringField(required=True)
    mobile = StringField(required=True)
    books = ListField(EmbeddedDocumentField(PurchasedBook))  
