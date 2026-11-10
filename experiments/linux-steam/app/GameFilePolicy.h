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
#endif
