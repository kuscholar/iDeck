// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
// Experimental case-insensitive path view scoped to this app's data and bundle.
// Does not change physical volume properties or iOS permissions.
#import <Foundation/Foundation.h>
#import <mach-o/dyld.h>
#import <dlfcn.h>
#import <dirent.h>
#import <errno.h>
#import <fcntl.h>
#import <stdarg.h>
#import <sys/stat.h>
#import <unistd.h>

static void *Libc(const char *symbol) {
    static void *handle;
    static dispatch_once_t once;
    dispatch_once(&once, ^{ handle = dlopen("/usr/lib/libSystem.B.dylib", RTLD_LAZY); });
    return dlsym(handle, symbol);
}
static NSString *Canonical(NSString *path) {
    char *(*fn)(const char *, char *) = Libc("realpath$DARWIN_EXTSN");
    char *result = fn ? fn(path.fileSystemRepresentation, NULL) : NULL;
    if (!result) return nil;
    NSString *value = @(result); free(result); return value;
}
static NSArray<NSString *> *Roots(void) {
    static NSArray *roots;
    static dispatch_once_t once;
    dispatch_once(&once, ^{
        int (*fn)(char *, uint32_t *) = Libc("_NSGetExecutablePath");
        char raw[PATH_MAX]; uint32_t size = sizeof raw;
        NSString *home = Canonical(NSHomeDirectory());
        NSString *bundle = fn && fn(raw, &size) == 0 ? Canonical([@(raw) stringByDeletingLastPathComponent]) : nil;
        NSMutableArray *list = [NSMutableArray new];
        if (home) [list addObject:home];
        if (bundle) [list addObject:bundle];
        roots = [list copy];
    });
    return roots;
}
static BOOL Under(NSString *path, NSString *root) {
    return [path isEqualToString:root] || [path hasPrefix:[root stringByAppendingString:@"/"]];
}
static BOOL Allowed(NSString *path) {
    for (NSString *root in Roots()) if (Under(path, root)) return YES;
    return NO;
}
static int caseViewReady;
void IDeckSetCaseViewReady(int ready) { __atomic_store_n(&caseViewReady, !!ready, __ATOMIC_RELEASE); }
int IDeckCaseViewReady(void) { return __atomic_load_n(&caseViewReady, __ATOMIC_ACQUIRE); }
int IDeckCaseViewContains(const char *path) {
    if (!path) return 0;
    @autoreleasepool {
        NSString *input = [[NSString alloc] initWithUTF8String:path];
        NSString *canonical = input ? Canonical(input) : nil;
        return canonical && Allowed(canonical);
    }
}
const char *IDeckCasePath(const char *path, char *buffer, size_t capacity) {
    if (!path) { errno = EFAULT; return NULL; }
    @autoreleasepool {
        NSString *input = [[NSString alloc] initWithUTF8String:path];
        if (!input) { errno = EILSEQ; return NULL; }
        if (![input isAbsolutePath]) {
            char cwd[PATH_MAX]; if (!getcwd(cwd, sizeof cwd)) return NULL;
            input = [@(cwd) stringByAppendingPathComponent:input];
        }
        input = [input stringByStandardizingPath];
        if ([input hasPrefix:@"/var/"]) input = [@"/private" stringByAppendingString:input];
        NSString *root = nil;
        for (NSString *candidate in Roots()) {
            if (input.length < candidate.length) continue;
            NSString *prefix = [input substringToIndex:candidate.length];
            if ([prefix caseInsensitiveCompare:candidate] == NSOrderedSame &&
                (input.length == candidate.length || [input characterAtIndex:candidate.length] == '/')) { root = candidate; break; }
        }
        if (!root) return path;
        NSString *current = root;
        int (*realStat)(const char *, struct stat *) = Libc("lstat");
        DIR *(*realOpenDir)(const char *) = Libc("opendir");
        for (NSString *component in [[input substringFromIndex:root.length] pathComponents]) {
            if ([component isEqualToString:@"/"] || !component.length) continue;
            NSString *canonicalParent = Canonical(current);
            if (canonicalParent && !Allowed(canonicalParent)) return path;
            NSString *next = [current stringByAppendingPathComponent:component];
            struct stat info;
            if (realStat(next.fileSystemRepresentation, &info) != 0) {
                DIR *directory = realOpenDir(current.fileSystemRepresentation);
                NSString *match = nil; struct dirent *entry;
                while (directory && (entry = readdir(directory))) {
                    NSString *name = [[NSString alloc] initWithUTF8String:entry->d_name];
                    if (!name || [name caseInsensitiveCompare:component] != NSOrderedSame) continue;
                    if (match) { closedir(directory); errno = EEXIST; return NULL; }
                    match = name;
                }
                if (directory) closedir(directory);
                if (match) next = [current stringByAppendingPathComponent:match];
            }
            current = next;
        }
        NSString *canonicalResult = Canonical(current);
        if (canonicalResult && !Allowed(canonicalResult)) return path;
        const char *value = current.fileSystemRepresentation;
        if (!value || strlen(value) >= capacity) { errno = ENAMETOOLONG; return NULL; }
        strlcpy(buffer, value, capacity); return buffer;
    }
}
int openat(int directory, const char *path, int flags, ...) {
    int mode = 0;
    if (flags & O_CREAT) { va_list args; va_start(args, flags); mode = va_arg(args, int); va_end(args); }
    if (!path) { errno = EFAULT; return -1; }
    if (path[0] == '/' || directory == AT_FDCWD) return open(path, flags, mode);
    char base[PATH_MAX], joined[PATH_MAX], resolved[PATH_MAX];
    if (fcntl(directory, F_GETPATH, base) != 0) return -1;
    if (snprintf(joined, sizeof joined, "%s/%s", base, path) >= (int)sizeof joined) { errno = ENAMETOOLONG; return -1; }
    const char *target = IDeckCasePath(joined, resolved, sizeof resolved);
    return target ? open(target, flags, mode) : -1;
}
