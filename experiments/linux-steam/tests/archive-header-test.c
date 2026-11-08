/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include <archive.h>
#include <archive_entry.h>
#include <locale.h>
#include <stdio.h>
#include <string.h>
static int failed;
static void check(const char *name,int ok){printf("%s=%s\n",name,ok?"PASS":"FAIL");if(!ok)failed++;}
static int header(const char *path,int binary){struct archive *a=archive_read_new();archive_read_support_filter_gzip(a);archive_read_support_format_tar(a);int result=archive_read_open_filename(a,path,65536);struct archive_entry *entry=NULL;if(result==ARCHIVE_OK)result=archive_read_next_header(a,&entry);if(binary&&result==ARCHIVE_OK){check("utf8-byte-path-exact",!strcmp(archive_entry_pathname(entry),"./copyright-\xc3\xa9.txt"));check("per-entry-binary-payload",archive_entry_size(entry)==1);char x=0;check("payload-preserved",archive_read_data(a,&x,1)==1&&x=='x');check("binary-eof",archive_read_next_header(a,&entry)==ARCHIVE_EOF);}archive_read_free(a);return result;}
int main(int argc,char **argv){if(argc!=4||!setlocale(LC_CTYPE,"C"))return 2;check("original-utf8-pax-C-warning",header(argv[1],0)==ARCHIVE_WARN);check("global-binary-is-insufficient",header(argv[2],0)==ARCHIVE_WARN);check("per-entry-binary-reads-in-C",header(argv[3],1)==ARCHIVE_OK);return failed?1:0;}
