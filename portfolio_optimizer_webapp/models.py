from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
import pandas as pd
import datetime

# TODO Clean up the data fields to be more efficent (e.g., divide by million, as int, etc.
#  Or at least convert int to IntegerFields. May cause issue with NAs?
# TODO user-specific entries?

def get_fiscal_year(date):
    assert date
    # Add fiscal year
    the_date = pd.to_datetime(date)
    fy_dates = {x: pd.to_datetime(f"{x}-12-31") for x in range(the_date.year - 1, datetime.date.today().year)}
    # get all differences with date as values
    cloz_dict = {abs(the_date.timestamp() - fydate.timestamp()): yr for yr, fydate in fy_dates.items()}
    # extracting minimum key using min()
    result = cloz_dict[min(cloz_dict.keys())]
    return result


class DataSettings(models.Model):
    
    class Meta:
        db_table = 'data_settings'
    
    OBJ_CHOICES = [
        ('max_sharpe', 'Maximum Sharpe Ratio'),
        ('min_volatility', 'Minimum Volatility'),
        ('max_quadratic_utility', 'Maximum Quadratic Utility')
    ]
    ESTIMATION_CHOICES = [
        ('nn', 'Neural Net'),
        ('lm', 'Linear Regression')
    ]

    start_date = models.DateField(default=datetime.date(2010, 1, 1))
    investment_amount = models.FloatField(default=10000)
    FScore_threshold = models.IntegerField(default=6)
    objective = models.CharField(default='max_sharpe', choices=OBJ_CHOICES, max_length=24)
    estimation_method = models.CharField(default='max_sharpe', choices=ESTIMATION_CHOICES, max_length=16)
    l2_gamma = models.FloatField(default=2)
    risk_aversion = models.FloatField(
        default=1,
        validators=[MinValueValidator(0.01), MaxValueValidator(1.0)],
        )


class SecurityList(models.Model):
    
    class Meta:
        db_table = 'security_list'

    symbol = models.CharField(max_length=12, primary_key=True)
    last_updated = models.DateTimeField(default=None, null=True)
    # first_created = models.DateTimeField(auto_now_add=True)
    # exchange_id = models.ForeignKey(Exchange, on_delete=models.CASCADE)
    # currency = models.CharField(default=None, null=True, max_length=3)
    name = models.CharField(default=None, null=True)
    country = models.CharField(default=None, null=True)
    sector = models.CharField(default=None, null=True)
    industry = models.CharField(default=None, null=True)
    # logo_url = models.CharField(default=None, null=True, max_length=100)
    fulltime_employees = models.IntegerField(default=None, null=True)
    business_summary = models.TextField(default=None, null=True, max_length=10000)
    # has_fundamentals = models.BooleanField(default=False)
    # has_securityprice = models.BooleanField(default=False)

    def __str__(self):
        return self.symbol

class Portfolio(models.Model):
    
    class Meta:
        db_table = 'portfolio'

    symbol = models.ForeignKey(SecurityList, on_delete=models.CASCADE, db_column='symbol')
    allocation = models.DecimalField(max_digits=10, null=True, decimal_places=6)
    shares = models.IntegerField(default=None, null=True)
    fiscal_year = models.IntegerField(default=None, null=True)

class Scores(models.Model):
    
    class Meta:
        db_table = 'scores'
    
    symbol = models.ForeignKey(SecurityList, on_delete=models.CASCADE, db_column='symbol')
    date = models.DateField(null=True)
    fiscal_year = models.IntegerField(default=None, null=True)
    pf_score = models.IntegerField(default=None, null=True)
    pf_score_weighted = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    eps = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    pe_ratio = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    roa = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    cash = models.BigIntegerField(default=None, null=True)
    cash_ratio = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    delta_cash = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    delta_roa = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    accruals = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    delta_long_lev_ratio = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    delta_current_lev_ratio = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    delta_shares = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    delta_gross_margin = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    delta_asset_turnover = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    # yearly_close = models.DecimalField(max_digits=17, null=True, decimal_places=2)
    # yearly_variance = models.DecimalField(max_digits=17, null=True, decimal_places=2)

    def save(self, *args, **kwargs):
        self.fiscal_year = get_fiscal_year(self.date)
        super(Scores, self).save(*args, **kwargs)

class SecurityPrice(models.Model):
    
    class Meta:
        db_table = 'security_price'
    
    symbol = models.ForeignKey(SecurityList, on_delete=models.CASCADE, db_column='symbol')
    date = models.DateField(null=True)
    open = models.DecimalField(max_digits=10, decimal_places=6)
    high = models.DecimalField(max_digits=10, decimal_places=6)
    low = models.DecimalField(max_digits=10, decimal_places=6)
    close = models.DecimalField(max_digits=10, decimal_places=6)
    adjclose = models.DecimalField(max_digits=10, decimal_places=6)
    # dividends = models.DecimalField(max_digits=10, decimal_places=6)
    # splits = models.IntegerField(default=None, null=True)
    volume = models.IntegerField(default=None, null=True)


class Fundamentals(models.Model):
    
    class Meta:
        db_table = 'fundamentals'
        unique_together = ('symbol', 'as_of_date', 'period_type', 'currency_code')
        
    symbol = models.ForeignKey(SecurityList, on_delete=models.CASCADE, db_column='symbol')
    as_of_date = models.DateField()
    period_type = models.CharField()
    net_income = models.BigIntegerField(default=None, null=True)
    net_income_common_stockholders = models.BigIntegerField(default=None, null=True)
    total_liabilities_net_minority_interest = models.BigIntegerField(default=None, null=True)
    total_assets = models.BigIntegerField(default=None, null=True)
    current_assets = models.BigIntegerField(default=None, null=True)
    current_liabilities = models.BigIntegerField(default=None, null=True)
    capital_stock = models.BigIntegerField(default=None, null=True)
    cash_and_cash_equivalents = models.BigIntegerField(default=None, null=True)
    gross_profit = models.BigIntegerField(default=None, null=True)
    total_revenue = models.BigIntegerField(default=None, null=True)
    currency_code = models.CharField(default=None, null=True, max_length=3)
    enterprise_value = models.BigIntegerField(default=None, null=True)
    enterprises_value_ebitda_ratio = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    enterprises_value_revenue_ratio = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    forward_pe_ratio = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    market_cap = models.BigIntegerField(default=None, null=True)
    pb_ratio = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    pe_ratio = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    peg_ratio = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)
    ps_ratio = models.DecimalField(max_digits=16, default=None, null=True, decimal_places=6)

    def save(self, *args, **kwargs):
        self.fiscal_year = get_fiscal_year(self.as_of_date)
        super(Fundamentals, self).save(*args, **kwargs)


balance_sheet = [
    'AccountsPayable', 'AccountsReceivable', 'AccruedInterestReceivable',
    'AccumulatedDepreciation', 'AdditionalPaidInCapital',
    'AllowanceForDoubtfulAccountsReceivable', 'AssetsHeldForSaleCurrent',
    'AvailableForSaleSecurities', 'BuildingsAndImprovements', 'CapitalLeaseObligations',
    'CapitalStock', 'CashAndCashEquivalents', 'CashCashEquivalentsAndShortTermInvestments',
    'CashEquivalents', 'CashFinancial', 'CommercialPaper', 'CommonStock',
    'CommonStockEquity', 'ConstructionInProgress', 'CurrentAccruedExpenses',
    'CurrentAssets', 'CurrentCapitalLeaseObligation', 'CurrentDebt',
    'CurrentDebtAndCapitalLeaseObligation', 'CurrentDeferredAssets',
    'CurrentDeferredLiabilities', 'CurrentDeferredRevenue', 'CurrentDeferredTaxesAssets',
    'CurrentDeferredTaxesLiabilities', 'CurrentLiabilities', 'CurrentNotesPayable',
    'CurrentProvisions', 'DefinedPensionBenefit', 'DerivativeProductLiabilities',
    'DividendsPayable', 'DuefromRelatedPartiesCurrent', 'DuefromRelatedPartiesNonCurrent',
    'DuetoRelatedPartiesCurrent', 'DuetoRelatedPartiesNonCurrent', 'EmployeeBenefits',
    'FinancialAssets', 'FinancialAssetsDesignatedasFairValueThroughProfitorLossTotal',
    'FinishedGoods', 'FixedAssetsRevaluationReserve', 'ForeignCurrencyTranslationAdjustments',
    'GainsLossesNotAffectingRetainedEarnings', 'GeneralPartnershipCapital', 'Goodwill',
    'GoodwillAndOtherIntangibleAssets', 'GrossAccountsReceivable', 'GrossPPE',
    'HedgingAssetsCurrent', 'HeldToMaturitySecurities', 'IncomeTaxPayable',
    'InterestPayable', 'InventoriesAdjustmentsAllowances', 'Inventory',
    'InvestedCapital', 'InvestmentProperties', 'InvestmentinFinancialAssets',
    'InvestmentsAndAdvances', 'InvestmentsInOtherVenturesUnderEquityMethod',
    'InvestmentsinAssociatesatCost', 'InvestmentsinJointVenturesatCost',
    'InvestmentsinSubsidiariesatCost', 'LandAndImprovements', 'Leases',
    'LiabilitiesHeldforSaleNonCurrent', 'LimitedPartnershipCapital',
    'LineOfCredit', 'LoansReceivable', 'LongTermCapitalLeaseObligation',
    'LongTermDebt', 'LongTermDebtAndCapitalLeaseObligation', 'LongTermEquityInvestment',
    'LongTermProvisions', 'MachineryFurnitureEquipment', 'MinimumPensionLiabilities',
    'MinorityInterest', 'NetDebt', 'NetPPE', 'NetTangibleAssets', 'NonCurrentAccountsReceivable',
    'NonCurrentAccruedExpenses', 'NonCurrentDeferredAssets', 'NonCurrentDeferredLiabilities',
    'NonCurrentDeferredRevenue', 'NonCurrentDeferredTaxesAssets', 'NonCurrentDeferredTaxesLiabilities',
    'NonCurrentNoteReceivables', 'NonCurrentPensionAndOtherPostretirementBenefitPlans',
    'NonCurrentPrepaidAssets', 'NotesReceivable', 'OrdinarySharesNumber',
    'OtherCapitalStock', 'OtherCurrentAssets', 'OtherCurrentBorrowings',
    'OtherCurrentLiabilities', 'OtherEquityAdjustments', 'OtherEquityInterest',
    'OtherIntangibleAssets', 'OtherInventories', 'OtherInvestments', 'OtherNonCurrentAssets',
    'OtherNonCurrentLiabilities', 'OtherPayable', 'OtherProperties', 'OtherReceivables',
    'OtherShortTermInvestments', 'Payables', 'PayablesAndAccruedExpenses',
    'PensionandOtherPostRetirementBenefitPlansCurrent', 'PreferredSecuritiesOutsideStockEquity',
    'PreferredSharesNumber', 'PreferredStock', 'PreferredStockEquity',
    'PrepaidAssets', 'Properties', 'RawMaterials', 'Receivables',
    'ReceivablesAdjustmentsAllowances', 'RestrictedCash', 'RestrictedCommonStock',
    'RetainedEarnings', 'ShareIssued', 'StockholdersEquity', 'TangibleBookValue',
    'TaxesReceivable', 'TotalAssets', 'TotalCapitalization', 'TotalDebt',
    'TotalEquityGrossMinorityInterest', 'TotalLiabilitiesNetMinorityInterest',
    'TotalNonCurrentAssets', 'TotalNonCurrentLiabilitiesNetMinorityInterest',
    'TotalPartnershipCapital', 'TotalTaxPayable', 'TradeandOtherPayablesNonCurrent',
    'TradingSecurities', 'TreasurySharesNumber', 'TreasuryStock', 'UnrealizedGainLoss',
    'WorkInProcess', 'WorkingCapital'
]

cash_flow = [
    'RepaymentOfDebt', 'RepurchaseOfCapitalStock', 'CashDividendsPaid',
    'CommonStockIssuance', 'ChangeInWorkingCapital',
    'CapitalExpenditure',
    'CashFlowFromContinuingFinancingActivities', 'NetIncome',
    'FreeCashFlow', 'ChangeInCashSupplementalAsReported',
    'SaleOfInvestment', 'EndCashPosition', 'OperatingCashFlow',
    'DeferredIncomeTax', 'NetOtherInvestingChanges',
    'ChangeInAccountPayable', 'NetOtherFinancingCharges',
    'PurchaseOfInvestment', 'ChangeInInventory',
    'DepreciationAndAmortization', 'PurchaseOfBusiness',
    'InvestingCashFlow', 'ChangesInAccountReceivables',
    'StockBasedCompensation', 'OtherNonCashItems',
    'BeginningCashPosition'
]

income_statement = [
    'Amortization', 'AmortizationOfIntangiblesIncomeStatement',
    'AverageDilutionEarnings', 'BasicAccountingChange', 'BasicAverageShares',
    'BasicContinuousOperations', 'BasicDiscontinuousOperations', 'BasicEPS',
    'BasicEPSOtherGainsLosses', 'BasicExtraordinary', 'ContinuingAndDiscontinuedBasicEPS',
    'ContinuingAndDiscontinuedDilutedEPS', 'CostOfRevenue', 'DepletionIncomeStatement',
    'DepreciationAmortizationDepletionIncomeStatement', 'DepreciationAndAmortizationInIncomeStatement',
    'DepreciationIncomeStatement', 'DilutedAccountingChange', 'DilutedAverageShares',
    'DilutedContinuousOperations', 'DilutedDiscontinuousOperations', 'DilutedEPS',
    'DilutedEPSOtherGainsLosses', 'DilutedExtraordinary', 'DilutedNIAvailtoComStockholders',
    'DividendPerShare', 'EBIT', 'EBITDA', 'EarningsFromEquityInterest',
    'EarningsFromEquityInterestNetOfTax', 'ExciseTaxes', 'GainOnSaleOfBusiness',
    'GainOnSaleOfPPE', 'GainOnSaleOfSecurity', 'GeneralAndAdministrativeExpense',
    'GrossProfit', 'ImpairmentOfCapitalAssets', 'InsuranceAndClaims',
    'InterestExpense', 'InterestExpenseNonOperating', 'InterestIncome',
    'InterestIncomeNonOperating', 'MinorityInterests', 'NetIncome', 'NetIncomeCommonStockholders',
    'NetIncomeContinuousOperations', 'NetIncomeDiscontinuousOperations',
    'NetIncomeExtraordinary', 'NetIncomeFromContinuingAndDiscontinuedOperation',
    'NetIncomeFromContinuingOperationNetMinorityInterest', 'NetIncomeFromTaxLossCarryforward',
    'NetIncomeIncludingNoncontrollingInterests', 'NetInterestIncome',
    'NetNonOperatingInterestIncomeExpense', 'NormalizedBasicEPS', 'NormalizedDilutedEPS',
    'NormalizedEBITDA', 'NormalizedIncome', 'OperatingExpense', 'OperatingIncome',
    'OperatingRevenue', 'OtherGandA', 'OtherIncomeExpense', 'OtherNonOperatingIncomeExpenses',
    'OtherOperatingExpenses', 'OtherSpecialCharges', 'OtherTaxes',
    'OtherunderPreferredStockDividend', 'PreferredStockDividends',
    'PretaxIncome', 'ProvisionForDoubtfulAccounts', 'ReconciledCostOfRevenue',
    'ReconciledDepreciation', 'RentAndLandingFees', 'RentExpenseSupplemental',
    'ReportedNormalizedBasicEPS', 'ReportedNormalizedDilutedEPS', 'ResearchAndDevelopment',
    'RestructuringAndMergernAcquisition', 'SalariesAndWages', 'SecuritiesAmortization',
    'SellingAndMarketingExpense', 'SellingGeneralAndAdministration', 'SpecialIncomeCharges',
    'TaxEffectOfUnusualItems', 'TaxLossCarryforwardBasicEPS', 'TaxLossCarryforwardDilutedEPS',
    'TaxProvision', 'TaxRateForCalcs', 'TotalExpenses', 'TotalOperatingIncomeAsReported',
    'TotalOtherFinanceCost', 'TotalRevenue', 'TotalUnusualItems',
    'TotalUnusualItemsExcludingGoodwill', 'WriteOff'
]
    
valuation_measures = [
    'ForwardPeRatio', 'PsRatio', 'PbRatio',
    'EnterprisesValueEBITDARatio', 'EnterprisesValueRevenueRatio',
    'PeRatio', 'MarketCap', 'EnterpriseValue', 'PegRatio'
]