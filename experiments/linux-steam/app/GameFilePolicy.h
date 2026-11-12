/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#ifndef IDECK_GAME_FILE_POLICY_H
#define IDECK_GAME_FILE_POLICY_H
#include <stdint.h>
struct ideck_launch_request;
/* Host-only registration API; a guest cannot register a native descriptor.
 * Call before guest execution. Retains one root capability for this one native
 * lifetime; no reusable teardown or all-native-clean certificate is implied.
 */
int ideck_game_file_policy_start(int data_directory);
/* Native shared-library root is explicit; never resolve it through fakefs data. */
int ideck_game_file_policy_start_shared(int data_directory,int shared_library_directory);
/* Observe a request synchronously; opens/validates/closes native game handles.
 * Always diagnostic: there is NO Wine/shell/process launch in this component.
 */
void ideck_game_file_policy_inspect(const struct ideck_launch_request *request);
struct ideck_game_file_observation {
    uint64_t submitted,completed_sequence;
    uint32_t appid;
    int status,library;
    unsigned machine;
};
int ideck_game_file_policy_observation(struct ideck_game_file_observation *out);
/* One bounded owned request snapshot. Diagnostic receipt only, NOT exclusive
 * storage/Wine/licensing permission. A second successful inspection remains
 * busy until native discard. Arguments stay in app memory for the launch contract;
 * never log/persist raw frames or interpret this receipt as a game exit. */
int ideck_game_file_policy_pending(struct ideck_launch_request *,uint64_t *sequence);
int ideck_game_file_policy_discard(uint64_t sequence);
#endif
