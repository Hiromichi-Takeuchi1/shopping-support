from pathlib import Path

from datetime import datetime
from pathlib import Path

from flask import Flask, abort, redirect, render_template, request, url_for
from sqlalchemy.exc import SQLAlchemyError

from models import Budget, Recipient, User, db


app = Flask(__name__)
database_path = Path(__file__).resolve().parent / "shopping_support.db"
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{database_path.as_posix()}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


def initialize_database():
    with app.app_context():
        db.create_all()

        test_user = User.query.filter_by(
            name="テストユーザー",
            age_group="子供",
        ).first()
        if test_user is None:
            db.session.add(User(name="テストユーザー", age_group="子供"))
            db.session.commit()


RECIPIENT_TYPES = {
    "family": {"name": "家族", "icon": "👨‍👩‍👧"},
    "grandparents": {"name": "おじいちゃん・おばあちゃん", "icon": "👴👵"},
    "self": {"name": "自分", "icon": "🙂"},
    "friends": {"name": "友達", "icon": "👫"},
}


@app.route("/budgets/new", methods=["GET", "POST"])
def budget_new():
    errors = []
    budget_summary = None
    form_data = request.form if request.method == "POST" else {}
    selected_types = request.form.getlist("recipient_types") if request.method == "POST" else []

    if request.method == "POST":
        title = form_data.get("title", "").strip()
        date_value = form_data.get("shopping_date", "")

        try:
            total_amount = int(form_data.get("total_amount", ""))
            if total_amount < 1:
                errors.append("全体予算は1円以上で入力してください")
        except ValueError:
            total_amount = 0
            errors.append("全体予算を1円以上で入力してください")

        try:
            shopping_date = datetime.strptime(date_value, "%Y-%m-%d").date()
        except ValueError:
            shopping_date = None
            errors.append("買い物をする日を入力してください")

        if not title:
            errors.append("買い物の名前を入力してください")

        valid_types = list(dict.fromkeys(
            recipient_type
            for recipient_type in selected_types
            if recipient_type in RECIPIENT_TYPES
        ))
        if not valid_types:
            errors.append("買う相手を1人以上選んでください")

        recipient_amounts = {}
        for recipient_type in valid_types:
            amount_value = form_data.get(f"amount_{recipient_type}", "")
            try:
                amount = int(amount_value)
                if amount < 1:
                    raise ValueError
                recipient_amounts[recipient_type] = amount
            except ValueError:
                errors.append(
                    f"{RECIPIENT_TYPES[recipient_type]['name']}の予算は1円以上で入力してください"
                )

        if (
            total_amount > 0
            and valid_types
            and len(recipient_amounts) == len(valid_types)
        ):
            recipient_total = sum(recipient_amounts.values())
            difference = total_amount - recipient_total
            budget_summary = {
                "total": total_amount,
                "allocated": recipient_total,
                "difference": difference,
            }
            if difference > 0:
                errors.append(
                    f"まだ {difference:,}円 のこっているよ。\n"
                    "だれに使うか決めてみよう！"
                )
            elif difference < 0:
                errors.append(
                    f"予算を {abs(difference):,}円 こえているよ。\n"
                    "もういちど金額を見てみよう！"
                )

        if not errors:
            try:
                user = User.query.filter_by(
                    name="テストユーザー",
                    age_group="子供",
                ).first()
                if user is None:
                    user = User(name="テストユーザー", age_group="子供")
                    db.session.add(user)
                    db.session.flush()

                budget = Budget(
                    user_id=user.id,
                    title=title,
                    total_amount=total_amount,
                    start_date=shopping_date,
                    end_date=shopping_date,
                )
                db.session.add(budget)
                db.session.flush()

                for recipient_type in valid_types:
                    recipient = RECIPIENT_TYPES[recipient_type]
                    db.session.add(
                        Recipient(
                            budget_id=budget.id,
                            name=recipient["name"],
                            icon_type=recipient_type,
                            budget_amount=recipient_amounts[recipient_type],
                        )
                    )

                db.session.commit()
                return redirect(url_for("budget_detail", budget_id=budget.id))
            except SQLAlchemyError:
                db.session.rollback()
                errors.append("保存に失敗しました。入力内容を確認してもう一度お試しください")

    return render_template(
        "budget_new.html",
        recipient_types=RECIPIENT_TYPES,
        selected_types=selected_types,
        form_data=form_data,
        errors=errors,
        budget_summary=budget_summary,
    )


@app.route("/budgets/<int:budget_id>")
def budget_detail(budget_id):
    budget = db.session.get(Budget, budget_id)
    if budget is None:
        abort(404)
    return render_template("budget_detail.html", budget=budget)


@app.route("/budgets/<int:budget_id>/recipients/new", methods=["GET", "POST"])
def recipient_new(budget_id):
    budget = db.session.get(Budget, budget_id)
    if budget is None:
        abort(404)

    errors = []
    form_data = request.form if request.method == "POST" else {}
    current_total = sum(recipient.budget_amount for recipient in budget.recipients)
    remaining_amount = max(budget.total_amount - current_total, 0)

    if request.method == "POST":
        if remaining_amount == 0:
            errors.append(
                "いまの予算はぜんぶ分けてあるよ。\n"
                "新しい相手を追加するなら、\n"
                "ほかの人の予算を少し変えてみよう！"
            )
        else:
            recipient_type = form_data.get("recipient_type", "")
            recipient_info = RECIPIENT_TYPES.get(recipient_type)
            if recipient_info is None:
                errors.append("買う相手を選んでね！")
            elif Recipient.query.filter_by(
                budget_id=budget.id,
                icon_type=recipient_type,
            ).first():
                errors.append(f"{recipient_info['name']}はもう登録されているよ！")
            else:
                try:
                    amount = int(form_data.get("budget_amount", ""))
                    if amount < 1:
                        errors.append("1円以上の金額を入れてね！")
                    elif amount > remaining_amount:
                        errors.append(
                            f"あと {remaining_amount:,}円 まで使えるよ。\n"
                            "金額をもういちど見てみよう！"
                        )
                except ValueError:
                    amount = 0
                    errors.append("1円以上の金額を入れてね！")

                if not errors:
                    db.session.add(
                        Recipient(
                            budget_id=budget.id,
                            name=recipient_info["name"],
                            icon_type=recipient_type,
                            budget_amount=amount,
                        )
                    )
                    try:
                        db.session.commit()
                        return redirect(url_for("budget_detail", budget_id=budget.id))
                    except SQLAlchemyError:
                        db.session.rollback()
                        errors.append("保存できなかったよ。もう一度試してね！")

    return render_template(
        "recipient_new.html",
        budget=budget,
        recipient_types=RECIPIENT_TYPES,
        remaining_amount=remaining_amount,
        selected_types=[form_data.get("recipient_type", "")],
        form_data=form_data,
        errors=errors,
    )


@app.route("/recipients/<int:recipient_id>/edit", methods=["GET", "POST"])
def recipient_edit(recipient_id):
    recipient = db.session.get(Recipient, recipient_id)
    if recipient is None:
        abort(404)
    budget = recipient.budget

    errors = []
    form_data = request.form if request.method == "POST" else {
        "recipient_type": recipient.icon_type,
        "budget_amount": str(recipient.budget_amount),
    }
    other_total = sum(
        item.budget_amount for item in budget.recipients if item.id != recipient.id
    )
    remaining_amount = max(budget.total_amount - other_total, 0)

    if request.method == "POST":
        recipient_type = form_data.get("recipient_type", "")
        recipient_info = RECIPIENT_TYPES.get(recipient_type)
        if recipient_info is None:
            errors.append("買う相手を選んでね！")
        elif Recipient.query.filter(
            Recipient.budget_id == budget.id,
            Recipient.icon_type == recipient_type,
            Recipient.id != recipient.id,
        ).first():
            errors.append(f"{recipient_info['name']}はもう登録されているよ！")
        else:
            try:
                amount = int(form_data.get("budget_amount", ""))
                if amount < 1:
                    errors.append("1円以上の金額を入れてね！")
                elif amount > remaining_amount:
                    errors.append(
                        f"あと {remaining_amount:,}円 まで使えるよ。\n"
                        "金額をもういちど見てみよう！"
                    )
            except ValueError:
                amount = 0
                errors.append("1円以上の金額を入れてね！")

            if not errors:
                recipient.name = recipient_info["name"]
                recipient.icon_type = recipient_type
                recipient.budget_amount = amount
                try:
                    db.session.commit()
                    return redirect(url_for("budget_detail", budget_id=budget.id))
                except SQLAlchemyError:
                    db.session.rollback()
                    errors.append("保存できなかったよ。もう一度試してね！")

    return render_template(
        "recipient_edit.html",
        budget=budget,
        recipient=recipient,
        recipient_types=RECIPIENT_TYPES,
        remaining_amount=remaining_amount,
        selected_types=[form_data.get("recipient_type", "")],
        form_data=form_data,
        errors=errors,
    )


if __name__ == "__main__":
    initialize_database()
    print(f"データベースを初期化しました: {database_path}")
    app.run(debug=True)