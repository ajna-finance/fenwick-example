import numpy as np

class FenwickScaleTree():
    def __init__(self, numBits):
        self.numBits=numBits
        self.n=2**numBits
        self.v=np.zeros(self.n+1)
        self.s = np.ones(self.n + 1)
        self.vv = np.zeros(self.n + 1)
    def scale(self,i):
        a=1.0
        while i<= self.n:
            a*=self.s[i]
            i+= i & (-i)
        return a

    def mult(self,i,f):
        for j in range(1+i):
            self.vv[j]*=f
        i+=1
        sum=0
        while i>0:
            sum += (f-1)*self.v[i] * self.s[i]
            self.s[i]*=f
            j=i+(i&(-i))
            i-=i&(-i)
            while ((j & (-j)) < (i & (-i))) or (i==0 and j<=self.n):
                self.v[j] += sum
                sum *= self.s[j]
                j += j&(-j)

    def increment(self, i, x):
        self.vv[i]+=x
        i+=1
        j=1 << (self.numBits)
        ii=0
        sc=1.0
        while j>0:
            if (i-1)&j:
                ii+=j
            else:
                if self.s[ii+j]==0:
                    self.s[ii + j]=1
                    self.v[ii + j]=0
                    k=j-1
                    while k>0:
                        self.s[ii+k]=0
                        k-= k&(-k)
                sc*=self.s[ii+j]
                self.v[ii+j]+=x/sc
            j = j >> 1

    def zerocumsum(self,i):
        s=0
        sc=1
        i+=1
        j=1 << (self.numBits)
        ii=0
        while j>0 and ii+j<=self.n:
            if i&j:
                s+=sc * self.s[ii+j]*self.v[ii+j]
            else:
                sc *= self.s[ii + j]
            ii=ii + (i&j)
            j= j >> 1
        return s

    def findcumsum(self, x):
        i = 1 << (self.numBits - 1)
        ss = 0
        sc = 1
        m = 0
        while i > 0:
            if ss + sc*self.s[m+i]*self.v[m + i] < x:
                m += i
                ss += sc*self.s[m]*self.v[m]
            else:
                sc *= self.s[m+i]
            i = i >> 1
        return m

    def rangesum(self, i,j):
        return self.zerocumsum(j)-self.zerocumsum(i-1)

    def valueAtIndex(self, i):
            i += 1
            s=self.v[i]
            j=i-1
            k=1
            while j&k:
                s -= self.s[j] * self.v[j]
                j=j-k
                k=k<<1
            while i <= self.n:
                s *= self.s[i]
                i += i & (-i)
            return s

    def vvzerocumsum(self,i):
        s=0
        for j in range(1+i):
            s+=self.vv[j]
        return s

    def check(self):
        for i in range(1,self.n-1):
            if abs(self.zerocumsum(i)-self.vvzerocumsum(i)) > 1e-10 * (self.zerocumsum(i)+self.vvzerocumsum(i)):
                print(f"CumSum Error at {i} {self.zerocumsum(i)} {self.vvzerocumsum(i)}")
                return False
            if abs(self.valueAtIndex(i) - self.vv[i]) > 1e-10 * (abs(self.valueAtIndex(i)) + abs(self.vv[i])):
                print(f'valueAtIndex Error at {i}  {self.valueAtIndex(i)} - {self.vv[i]}')
                return False

        return True

if __name__ == '__main__':
    z=FenwickScaleTree(10)
    for i in range(1,1000):
        z.increment(i,np.random.rand())
    for i in range(100):
        z.mult(np.random.randint(1,1000),1.0+0.02*np.random.rand())
        z.increment(np.random.randint(1,1000),np.random.rand())
    for i in range(100):
        z.mult(np.random.randint(1,1000),1.0+0.02*np.random.rand())
        z.increment(np.random.randint(1,1000),np.random.rand())
    for i in range(100):
        z.mult(np.random.randint(1,1000),1.0+0.02*np.random.rand())
        z.increment(np.random.randint(1,1000),np.random.rand())
    for i in range(1,1024):
        print(f'i={i} valueAtIndex={z.valueAtIndex(i)} computed={z.zerocumsum(i)-z.zerocumsum(i-1)}')
    print(f"findcumsum of 0 ={z.findcumsum(0)}")
    print(z.check())
    print(f"item {512} is {z.v[512]} {sum([z.vv[i] for i in range(512)])}")
    print(f"item {z.n} is {z.v[z.n]} {sum([z.vv[i] for i in range(1,z.n)])}")
    print(f"item {z.n-1} is {z.v[z.n-1]} {z.vv[z.n-1]}")


