// SPDX-License-Identifier: GPL-3.0-or-later
#import <Foundation/Foundation.h>
#include <assert.h>
extern const CGFloat *NSFontIdentityMatrix;
int main(void) {
    assert(NSFontIdentityMatrix);
    const CGFloat identity[]={1,0,0,1,0,0};
    for(int i=0;i<6;++i)assert(NSFontIdentityMatrix[i]==identity[i]);
    puts("NSFontIdentityMatrix: pointer-to-six-CGFloat DATA ABI PASS");
}
