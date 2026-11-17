import stripe


def charge(token):
    return stripe.Charge.create(amount=100, currency="usd", source=token)


def other():
    return stripe.Customer.create(email="a@b.c")
