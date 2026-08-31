#pragma once

#include <map>
#include <string>
#include <vector>

/// Generate deterministic inputs and their complete fixed-point reference.
/// Each value contains one text row per RTL cycle or reference frame.
std::map<std::string, std::vector<std::string>> reference_frames(int n_frames = 10);
