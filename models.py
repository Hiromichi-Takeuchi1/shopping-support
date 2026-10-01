from datetime import datetime

from flask_sqlalchemy import SQLAlchemy


# 全モデルで共通して使うデータベースオブジェクトです。
db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age_group = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    # relationshipを使うと、関連するレコードをPythonからたどれます。
    budgets = db.relationship("Budget", back_populates="user")


class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    total_amount = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    memo = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    user = db.relationship("User", back_populates="budgets")
    recipients = db.relationship("Recipient", back_populates="budget")
    purchases = db.relationship("Purchase", back_populates="budget")


class Recipient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    budget_id = db.Column(db.Integer, db.ForeignKey("budget.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    icon_type = db.Column(db.String(50), nullable=False)
    budget_amount = db.Column(db.Integer, nullable=False)
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    budget = db.relationship("Budget", back_populates="recipients")
    items = db.relationship("Item", back_populates="recipient")
    purchases = db.relationship("Purchase", back_populates="recipient")


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey("recipient.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    memo = db.Column(db.Text, nullable=True)
    is_purchased = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    recipient = db.relationship("Recipient", back_populates="items")


class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    budget_id = db.Column(db.Integer, db.ForeignKey("budget.id"), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey("recipient.id"), nullable=False)
    item_name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    purchased_at = db.Column(db.DateTime, nullable=False)
    memo = db.Column(db.Text, nullable=True)

    budget = db.relationship("Budget", back_populates="purchases")
    recipient = db.relationship("Recipient", back_populates="purchases")