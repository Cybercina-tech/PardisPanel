from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from category.models import Category, Currency, PriceType
from change_price.models import PriceHistory


def _currency(code):
    obj, _ = Currency.objects.get_or_create(code=code, defaults={"name": code})
    return obj


class DropOtherUsdtTomanTest(TestCase):
    def setUp(self):
        usdt, irt, gbp, eur = _currency("USDT"), _currency("IRT"), _currency("GBP"), _currency("EUR")
        other = Category.objects.create(name="سایر ارز ها")
        tether = Category.objects.create(name="تتر")
        self.buy = PriceType.objects.create(
            category=other, name="خرید تتر به تومن", source_currency=usdt, target_currency=irt, trade_type="buy"
        )
        self.sell = PriceType.objects.create(
            category=other, name="فروش تتر به تومن", source_currency=irt, target_currency=usdt, trade_type="sell"
        )
        self.usdt_gbp = PriceType.objects.create(
            category=other, name="خرید تتر به پوند", source_currency=usdt, target_currency=gbp, trade_type="buy"
        )
        self.euro = PriceType.objects.create(
            category=other, name="یورو", source_currency=eur, target_currency=irt, trade_type="sell"
        )
        self.elsewhere = PriceType.objects.create(
            category=tether, name="خرید تتر", source_currency=usdt, target_currency=irt, trade_type="buy"
        )
        PriceHistory.objects.create(price_type=self.buy, price=Decimal("1"))

    def _remaining(self):
        return set(PriceType.all_objects.values_list("id", flat=True))

    def test_deletes_only_usdt_toman_in_other_currencies(self):
        call_command("drop_other_usdt_toman", stdout=StringIO())
        self.assertEqual(self._remaining(), {self.usdt_gbp.id, self.euro.id, self.elsewhere.id})
        self.assertFalse(PriceHistory.all_objects.filter(price_type_id=self.buy.id).exists())

    def test_dry_run_changes_nothing(self):
        out = StringIO()
        call_command("drop_other_usdt_toman", "--dry-run", stdout=out)
        self.assertIn("(1 history rows)", out.getvalue())
        self.assertEqual(len(self._remaining()), 5)
