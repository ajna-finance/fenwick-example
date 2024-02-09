import numpy as np
from fenwickscaletree import FenwickScaleTree

class AjnaLender:
    def __init__(self, name, priceIndex, lpb):
        self.name = name
        self.priceIndex=priceIndex
        self.lpb=lpb
        return
    def addDeposit(self, amount):
        self.lpb += amount
        return self.deposit
    def withdrawDeposit(self, amount):
        self.lpb -= amount
    def __str__(self):
        return (f"Lender: {self.name} LPB: {self.lpb}")

class AjnaLoan:
    def __init__(self, name, borrowerInflator):
        self.collateral=0
        self.debt=0
        self.borrowerInflatorSnapshot=borrowerInflator
        self.name=name
        return
    def accrueInterest(self, borrowerInflator):
        self.debt *= borrowerInflator/self.borrowerInflatorSnapshot
        self.borrowerInflatorSnapshot=borrowerInflator
        return self.debt
    def depositCollateral(self, amount, borrowerInflator):
        self.accrueInterest(borrowerInflator)
        self.collateral+= amount
        return self.collateral
    def withdrawCollateral(self, amount, lup, borrowerInflator):
        self.accrueInterest(borrowerInflator)
        if self.debt <= lup*(self.collateral-amount):
            self.collateral -= amount
            return self.collateral
        else:
            raise Exception("Not enough collateral to withdraw")
    def borrow(self, amount, lup, borrowerInflator):
        self.accrueInterest(borrowerInflator)
        if (self.debt + amount) <= lup*self.collateral:
            self.debt += amount
            return amount
        else:
            raise Exception("Not enough collateral to borrow")
        return
    def repay(self, amount, borrowerInflator):
        self.accrueInterest(borrowerInflator)
        self.debt-=amount
        return amount
    def getThresholdPrice(self, borrowerInflator):
        self.accrueInterest(borrowerInflator)
        return self.debt / self.collateral
    def __str__(self):
        return f"Loan: {self.name} Collateral: {self.collateral:6.2f} Debt: {self.debt} Inflator: {self.borrowerInflatorSnapshot}"

class AjnaPool:
    def __init__(self, nBits):
        self.n=2**nBits
        self.nBits=nBits
        self.deposits = FenwickScaleTree(nBits)
        self.lpb =np.zeros(self.n)
        self.borrowerDebt = 0
        self.lenderDebt = 0
        self.loans = []
        self.borrowerInflator = 1
        self.borrowerInflatorSnapshotTime = 0
        self.depositors = {}
        self.time=0
        self.interestRate = 0.001
        self.lenderInterestFactor = 0.9
        self.origFee = 0.002
        self.qt = 0

    def accrueInterest(self):
        dt=self.time-self.borrowerInflatorSnapshotTime
        self.borrowerInflatorSnapshotTime=self.time
        factor = np.exp(self.interestRate * dt)
        newInterest =  self.lenderInterestFactor *(factor-1)*self.borrowerDebt
        self.borrowerInflator *= factor
        self.borrowerDebt *= factor
        if self.depositAboveHTP() > 0:
            lenderFactor = 1.0 + newInterest/self.depositAboveHTP()
            self.deposits.mult(self.priceToIndex(self.HTP()), lenderFactor)
        return self.borrowerInflator

    def price(self,k):
        return (self.n-k)

    def priceToIndex(self,p):
        return int(max(0,min(self.n-1,np.round(self.n-p))))

    def depositAboveHTP(self):
        return self.deposits.zerocumsum(self.priceToIndex(self.HTP()))

    def LUP(self, amount=0):
        return self.deposits.findcumsum(self.lenderDebt+amount)
    def lpbExchangeRate(self, priceIndex):
        if self.lpb[priceIndex] == 0:
            return 1.0
        else:
            return self.deposits.rangesum(priceIndex,priceIndex)/self.lpb[priceIndex]

    def addDeposit(self, depositor, priceIndex, depositAmount):
        self.accrueInterest()
        lpbAmount = depositAmount/self.lpbExchangeRate(priceIndex)
        self.lpb[priceIndex] += lpbAmount
        self.deposits.increment(priceIndex, depositAmount)
        self.qt+=depositAmount
        if depositor not in self.depositors:
            self.depositors[depositor] = AjnaLender(depositor, priceIndex, lpbAmount)
        else:
            if priceIndex != self.depositors[depositor].priceIndex:
                raise Exception("Depositor already has a deposit at a different price index")
            self.depositors[depositor].addDeposit(lpbAmount)

    def redeemLPB(self, depositor, priceIndex, lpbAmount):
        self.accrueInterest()
        depositAmount = lpbAmount*self.lpbExchangeRate(priceIndex)
        if depositor not in self.depositors:
            raise Exception("Depositor does not have a deposit")
        if priceIndex != self.depositors[depositor].priceIndex:
            raise Exception("Depositor does not have a deposit at this price index")
        if lpbAmount > self.depositors[depositor].lpb:
            raise Exception("Depositor does not have this much deposit")
        if priceIndex>=self.LUP():
            proposedLUP = self.deposits.findcumsum(self.lenderDebt + depositAmount)
        else:
            proposedLUP = self.LUP()
        if self.HTP() > self.price(proposedLUP):
            raise Exception("Depositor would move LUP below HTP")
        self.depositors[depositor].withdrawDeposit(lpbAmount)
        self.deposits.increment(priceIndex, -depositAmount)
        self.qt -= depositAmount

    def depositCollateral(self, name, amount):
        self.accrueInterest()
        loan = self.getLoanByName(name)
        if loan:
            loan.depositCollateral(amount, self.borrowerInflator)
        else:
            loan = AjnaLoan(name, self.borrowerInflator)
            loan.depositCollateral(amount, self.borrowerInflator)
        self.addLoan(loan)

    def withdrawCollateral(self, name, amount):
        self.accrueInterest()
        self.getLoanByName(name).withdrawCollateral(amount, self.borrowerInflator)
        self.addLoan(loan)

    def borrow(self, name, amount):
        self.accrueInterest()
        loan = self.getLoanByName(name)
        loan.borrow(amount, self.price(self.LUP(amount)), self.borrowerInflator)
        self.addLoan(loan)
        self.borrowerDebt += (1+self.origFee)*amount
        self.lenderDebt += amount
        self.qt -=  amount

    def repay(self, name, amount):
        self.accrueInterest()
        loan = self.getLoanByName(name)
        loan.repayl(amount, self.borrowerInflator)
        self.addLoan(loan)
        self.borrowerDebt -= amount
        self.lenderDebt -= self.lenderDebt/self.borrowerDebt * amount

    def getLoanByName(self, name):
        for loan in self.loans:
            if loan.name == name:
                return loan
        return None

    def addLoan(self, loanToAdd):
        for loan in self.loans:
            if loan.name == loanToAdd.name:
                self.loans.remove(loan)
        i=0
        while (i<len(self.loans)) and \
                (loanToAdd.getThresholdPrice(self.borrowerInflator) > self.loans[i].getThresholdPrice(self.borrowerInflator)):
            i+=1
        self.loans.insert(i, loanToAdd)

    def HTP(self):
        if len(self.loans) == 0:
            return self.n
        return self.loans[0].getThresholdPrice(self.borrowerInflator)

    def printPool(self):
        print("----------------------------------------------------")
        print(f"Time: {self.time}")
        for i in range(self.n):
            if self.lpb[i]>0:
                print(f"{i:3d}  {self.price(i):8.2f}    {self.deposits.rangesum(i,i):8.2f}")
        print(f"")
        print(f"LUP: {self.LUP()}")
        print(f"HTP: {self.HTP()}")
        print(f"HTP index: {self.priceToIndex(self.HTP())}")
        print(f"Deposit Above HTP: {self.depositAboveHTP()}")
        print(f"Lender Debt: {self.lenderDebt}")
        print(f"Borrower Debt: {self.borrowerDebt}")
        print("Depositors: ")
        for name,depositor in self.depositors.items():
            print(str(depositor))
        print("Loans: ")
        for loan in self.loans:
            print(str(loan))
        print("")

if __name__ == '__main__':

    pool = AjnaPool(13)
    pool.depositCollateral("A", 50)
    pool.depositCollateral("B", 50)
    for i in range(5):
        pool.addDeposit(chr(97+i), 1000+i, 100+100*i)
    pool.printPool()

    pool.borrow("A", 500)
    pool.printPool()
    pool.time += 10
    pool.accrueInterest()
    pool.printPool()
    pool.borrow("B", 300)
    pool.time +=20
    pool.accrueInterest()
    pool.printPool()


