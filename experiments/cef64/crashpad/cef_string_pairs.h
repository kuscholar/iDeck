// Copyright 2012 The Chromium Authors
// Copyright 2026 iDeck contributors
// Chromium-derived parsing retains Chromium's BSD license; see
// https://github.com/chromium/chromium/blob/2e81dea53f5ecdc1c057e4c70ecd66151987296a/LICENSE
// Standalone adaptation of base/strings/string_split.cc for CEF crash-key names.
// Never log the input or the resulting key/value payloads.
#ifndef IDECK_CEF_STRING_PAIRS_H_
#define IDECK_CEF_STRING_PAIRS_H_

#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace ideck_cef {
using StringPairs = std::vector<std::pair<std::string, std::string>>;

inline bool SplitStringIntoKeyValuePairs(std::string_view input,
                                        char key_value_delimiter,
                                        char pair_delimiter,
                                        StringPairs* output) {
  output->clear();
  bool success = true;
  while (!input.empty()) {
    const size_t end = input.find(pair_delimiter);
    auto pair = input.substr(0, end);
    // Chromium TRIM_WHITESPACE / SPLIT_WANT_NONEMPTY for ASCII strings.
    constexpr std::string_view whitespace(" \t\n\v\f\r");
    const size_t start = pair.find_first_not_of(whitespace);
    if (start != std::string_view::npos) {
      pair = pair.substr(start, pair.find_last_not_of(whitespace) - start + 1);
      output->emplace_back();  // Upstream keeps an entry even on parse failure.
      const size_t separator = pair.find(key_value_delimiter);
      if (separator == std::string_view::npos) {
        success = false;
      } else {
        output->back().first = std::string(pair.substr(0, separator));
        const size_t value = pair.find_first_not_of(key_value_delimiter, separator);
        if (value == std::string_view::npos) {
          success = false;
        } else {
          output->back().second = std::string(pair.substr(value));
        }
      }
    }
    if (end == std::string_view::npos) break;
    input.remove_prefix(end + 1);
  }
  return success;
}
}  // namespace ideck_cef
#endif
