import numpy as np

class AbstractCumList:
    def __init__(self, numBits):
        self.numBits=numBits
        self.n=2**numBits
        self.val=np.zeros(self.n+1)
    def increment(self, i, x):
        i+=1
        while i<=self.n:
            self.val[i]+=x
            i+=i & (-i)
    def zerocumsum(self,i):
        s=0
        i+=1
        while i>0:
            s+=self.val[i]
            i-=i&(-i)
        return s
    def cumsum(self,i,j):
        return self.zerocumsum(j)-self.zerocumsum(i-1)
    def findcumsum(self,s):
        i=2**(self.numBits-1)
        ss = 0
        m=0
        while i>0:
            if ss+self.val[m+i] < s:
                ss+=self.val[m+i]
                m+=i
            i=i>>1
        return m


class AjnaLoan:
    def __init__(self, name, borrowerInflator):
        self.collateral=0
        self.principal=0
        self.interest=0
        self.borrowerInflatorSnapshot=borrowerInflator
        self.name=name
        return
    def accrueInterest(self, borrowerInflator):
        self.interest += (borrowerInflator)
        self.borrowerInflatorSnapshot=borrowerInflator
        return self.interest
    def depositCollateral(self, amount):
        self.collateral+= amount
        return self.collateral
    def withdrawCollateral(self, amount, lup):
        if (self.principal + self.interest) <= lup*(self.collateral-amount):
            self.collateral -= amount
            return self.collateral
        else:
            raise Exception("Not enough collateral to withdraw")
    def borrow(self, amount, lup, borrowerInflator):
        self.accrueInterest(borrowerInflator)
        if (self.principal + self.interest + amount) <= lup*self.collateral:
            self.principal += amount
            return amount
        else:
            raise Exception("Not enough collateral to borrow")
        return
    def repay(self, amount, borrowerInflator):
        self.accrueInterest(borrowerInflator)
        amount -= repayInterest(min(amount, self.interest))
        amount -= repayPrincipal(min(amount, self.principal))
        return amount
    def repayInterest(self, amount, borrowerInflator):
        self.accrueInterest(borrowerInflator)
        if amount > self.interest:
            raise Exception("Not enough interest to repay")
        self.interest -= amount
        return self.interest
    def repayPrincipal(self, amount, borrowerInflator):
        self.accrueInterest(borrowerInflator)
        if amount > self.principal:
            raise Exception("Not enough principal to repay")
        self.principal -= amount
        return self.principal
    def getThresholdPrice(self):
        return (self.principal + self.interest) / self.collateral
    def __str__(self):
        return "Loan: "+self.name+"\nCollateral: "+str(self.collateral)+"\nPrincipal: "+str(self.principal)+"\nInterest: "+str(self.interest)

class AjnaLender:
    def __init__(self, priceIndex, deposit, priceIndexInterestInflator, name):
        self.name = name
        self.priceIndex=priceIndex
        self.deposit=deposit
        self.priceIndexInterestInflatorSnapshot=priceIndexInterestInflator
        return
    def accrueInterest(self, priceIndexInterestInflator):
        self.interest += (priceIndexInterestInflator-self.priceIndexInterestInflatorSnapshot)*self.deposit
        self.priceIndexInterestInflatorSnapshot=priceIndexInterestInflator
        return self.priceIndexInterestInflatorSnapshot
    def addDeposit(self, amount, priceIndexInterestInflator):
        self.accrueInterest(priceIndexInterestInflator)
        self.deposit += amount
        return self.deposit
    def withdrawDeposit(self, amount, priceIndexInterestInflator):
        self.accrueInterest(priceIndexInterestInflator)
        self.deposit -= amount
    def claimInterest(self, amount, priceIndexInterestInflator):
        self.accrueInterest(priceIndexInterestInflator)
        if amount > self.interest:
            raise Exception("Not enough interest to claim")
        self.interest -= amount
        return self.interest
    def __str__(self):
        return ("Lender: "+self.name+"\nDeposit: "+str(self.deposit)+"\nprice: "+str(self.priceIndex)+
                "\nInterestInflatorSnapshot: "+str(self.priceIndexInterestInflatorSnapshot))

class AjnaPool:
    def __init__(self, nBits):
        self.n=2**nBits
        self.nBits=nBits
        self.deposits = AbstractCumList(nBits)
        self.interestAccum = AbstractCumList(nBits)
        self.interest = np.array([0]*(self.n+1))
        self.interestAccumSnapshot = np.array([0]*(self.n+1))
        self.totalPrincipal = 0
        self.interestPool = 0
        self.depositAboveHtp = 0
        self.totalInterest = 0
        self.loans = []
        self.borrowerInflator = 0
        self.borrowerInflatorSnapshotTime = 0
        self.depositors = {}
        self.LUPIndex = self.n-1
        self.time=0
        self.interestRate = 0.05
    def accrueInterest(self):
        dt=self.time-self.borrowerInflatorSnapshotTime
        self.borrowerInflator += dt*self.interestRate
        if self.totalPrincipal > 0:
            newInterest = dt*self.interestRate*self.totalPrincipal/self.depositAboveHtp
            self.totalInterest += newInterest
            self.interestAccum.increment(self.time, newInterest)
        self.borrowerInflatorSnapshotTime = self.time
        return self.borrowerInflator
    def accrueBucketInterest(self, priceIndex):
        self.accrueInterest()
        interestAccumulator = self.interestAccum.cumsum(0, priceIndex)
        self.interest[priceIndex] += (self.interestAccumSnapshot[priceIndex] - interestAccumulator)*self.deposits.cumsum(priceIndex,priceIndex)
        self.interestAccumSnapshot[priceIndex] = interestAccumulator
        return self.interest[priceIndex]
    def updateLUP(self):
        self.LUPIndex = self.deposits.findcumsum(self.totalPrincipal)
    def addDeposit(self, depositor, priceIndex, amount):
        self.accrueBucketInterest(priceIndex)
        if depositor not in self.depositors:
            self.depositors[depositor] = AjnaLender(priceIndex,
                                                    amount,
                                                    self.interestAccum.cumsum(0, priceIndex),
                                                    depositor)
        else:
            if priceIndex != self.depositors[depositor].priceIndex:
                raise Exception("Depositor already has a deposit at a different price index")
            self.depositors[depositor].addDeposit(amount, self.interestAccum.cumsum(0, priceIndex))
        self.deposits.increment(priceIndex, amount)
        if priceIndex > self.LUPIndex:
            self.updateLUP()
    def removeDeposit(self, depositor, priceIndex, amount):
        self.accrueBucketInterest(priceIndex)
        if depositor not in self.depositors:
            raise Exception("Depositor does not have a deposit")
        if priceIndex != self.depositors[depositor].priceIndex:
            raise Exception("Depositor does not have a deposit at this price index")
        if amount > self.depositors[depositor].deposit:
            raise Exception("Depositor does not have this much deposit")
        if priceIndex>=self.LUPIndex:
            proposedLUP = self.deposits.findcumsum(self.totalPrincipal + amount)
        else:
            proposedLUP = self.LUPIndex
        if self.HTP() > proposedLUP:
            raise Exception("Depositor would move LUP below HTP")
        self.depositors[depositor].withdrawDeposit(amount, self.interestAccum.cumsum(0, priceIndex))
        self.deposits.increment(priceIndex, -amount)
        self.LUPIndex = proposedLUP

    def claimInterest(self, depositorName, amount):
        if self.interestPool < amount:
            raise Exception("Not enough interest to claim")
        depositor = self.depositors[depositorName]
        depositor.claimInterest(amount, self.interestAccum.cumsum(0, depositor.priceIndex))
        self.interestPool -= amount
        self.interest[depositor.priceIndex] -= amount
        return amount

    def depositCollateral(self, name, amount):
        self.accrueInterest()
        loan = self.getLoanByName(name)
        if loan:
            loan.depositCollateral(amount, self.borrowerInflator)
        else:
            loan = AjnaLoan(name, self.borrowerInflator)
            loan.depositCollateral(amount)
        self.addLoan(loan)

    def withdrawCollateral(self, name, amount):
        self.accrueInterest()
        oldHTP = self.HTP()
        self.getLoanByName(name).withdrawCollateral(amount, self.borrowerInflator)
        self.addLoan(loan)
        if oldHTP != self.HTP():
            self.depositAboveHtp = self.deposits.cumsum(self.HTP(), self.n-1)

    def borrow(self, name, amount):
        self.accrueInterest()
        oldHTP = self.HTP()
        loan = self.getLoanByName(name)
        loan.borrow(amount, self.LUPIndex, self.borrowerInflator)
        self.addLoan(loan)
        self.totalPrincipal += amount
        if oldHTP != self.HTP():
            self.depositAboveHtp = self.deposits.cumsum(self.HTP(), self.n-1)

    def repayPrincipal(self, name, amount):
        self.accrueInterest()
        oldHTP = self.HTP()
        loan = self.getLoanByName(name)
        loan.repayPrincipal(amount, self.borrowerInflator)
        self.addLoan(loan)
        self.totalPrincipal -= amount
        if oldHTP != self.HTP():
            self.depositAboveHtp = self.deposits.cumsum(self.HTP(), self.n-1)

    def repayInterest(self, name, amount):
        self.accrueInterest()
        oldHTP = self.HTP()
        loan = self.getLoanByName(name)
        loan.repayInterest(amount, self.borrowerInflator)
        self.totalInterest -= amount
        self.interestPool += amount
        if oldHTP != self.HTP():
            self.depositAboveHtp = self.deposits.cumsum(self.HTP(), self.n-1)

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
        while (i<len(self.loans)) and (loanToAdd.getThresholdPrice() > self.loans[i].getThresholdPrice()):
            i+=1
        self.loans.insert(i, loanToAdd)

    def HTP(self):
        if len(self.loans) == 0:
            return None
        return int(self.loans[0].getThresholdPrice())

    def printPool(self):
        print("----------------------------------------------------")
        print("Interest Pool: " + str(self.interestPool) + "\n")
        for i in range(self.n):
            dep,int,iacc,iaccsnapshot = self.deposits.cumsum(i,i),self.interest[i],self.interestAccum.cumsum(i,i),self.interestAccumSnapshot[i]
            if dep+int+iacc+iaccsnapshot > 0:
                print(i,dep,int,iacc,iaccsnapshot)
        print("")
        print("LUP: " + str(self.LUPIndex))
        print("Deposit Above HTP: " + str(self.depositAboveHtp))
        print("Borrower Inflator: " + str(self.borrowerInflator))
        print("Borrower Inflator Snapshot: " + str(self.borrowerInflator))
        print("Borrower Inflator Snapshot Time: " + str(self.borrowerInflatorSnapshotTime))
        print("Depositors: ")
        for name,depositor in self.depositors.items():
            print(str(depositor))
        print("Loans: ")
        for loan in self.loans:
            print(str(loan))
        print("")


if __name__ == '__main__':

    # testing fenwick tree including findcumsum
    if False:
        tv = AbstractCumList(13)
        for i in range(100,200):
            tv.increment(i, i)
        print(tv.cumsum(0, 100))
        print(tv.cumsum(120, 150))
        print(tv.cumsum(0, 200))
        for i in range(300):
            print(i, tv.findcumsum(tv.cumsum(0, i)))

    pool = AjnaPool(13)
    pool.depositCollateral("A", 1000)
    pool.addDeposit("a", 1000, 100)
    pool.printPool()

    pool.borrow("A", 5000)
    pool.printPool()

