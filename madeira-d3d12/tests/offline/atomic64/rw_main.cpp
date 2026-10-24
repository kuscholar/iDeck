// Host driver for src/unix/madeira_ags.cpp: rw in.dxbc out.dxbc
#include <cstdio>
#include <cstdlib>
extern "C" int madeira_ags_rewrite(const void *, size_t, void **, size_t *, char *, size_t);
int main(int argc, char **argv) {
    FILE *f = fopen(argv[1], "rb"); if (!f) return 2;
    fseek(f, 0, SEEK_END); size_t n = ftell(f); rewind(f);
    void *b = malloc(n); fread(b, 1, n, f); fclose(f);
    void *o = nullptr; size_t on = 0; char note[256];
    int rc = madeira_ags_rewrite(b, n, &o, &on, note, sizeof note);
    printf("rc=%d note='%s' out=%zu bytes\n", rc, note, on);
    if (rc == 1 && argc > 2) { f = fopen(argv[2], "wb"); fwrite(o, 1, on, f); fclose(f); }
    return rc < 0;
}
