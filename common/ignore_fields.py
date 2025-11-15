# fields to ignore in getting keywords
IGNORE_FIELDS = [
    "id",
    "uuid",
    "password",
    "metadata",
    "refs",
    "prefs",
    "verification_code",
    "verification_code_expiry",
    "last_login",
    "comment",
    "opt_out",
]

# common words to ignore in keywords
IGNORE_WORDS = {
    "this", "that", "in", "to", "the", "what", "if", "and", "or", "but", "for", "with", "on", "at", "by", "from", "of", "a", "an", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "could", "should", "can", "may", "might", "must", "shall", "it", "its", "it's", "i", "you", "he", "she", "they", "we", "us", "me", "him", "her", "them", "my", "your", "his", "our", "their", "as", "so", "then", "than", "when", "where", "why", "how", "all", "some", "any", "every", "each", "no", "not", "yes", "ok", "okay", "true", "false", "yes", "no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"
}
