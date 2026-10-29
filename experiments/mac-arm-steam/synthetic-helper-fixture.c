// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
// Own fixture, not a substituted Steam UI/helper or process identity model.
static int Constructors;
static int MainCalls;
__attribute__((constructor)) static void Start(void){++Constructors;}
__attribute__((visibility("default"))) const char *IDeckFixtureMarker(void){return "IDeckSyntheticHelperFixture-v1";}
__attribute__((visibility("default"))) int IDeckFixtureRead(void){return 100*Constructors+MainCalls;}
int main(void){++MainCalls;return 0;}
