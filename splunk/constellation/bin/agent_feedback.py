"""Factual response checks independent of the model and provider adapter."""
import re
from provider_service import ProviderError


def validate_data_claims(result, profile):
    if not profile or not profile.get('sampledRows') or result.get('changes'):
        return
    message = result.get('message', '')
    missing = re.search(r'\b(?:no|zero)\s+(?:(?:matching|searchable|available|recent)\s+)?(?:events|rows|results)\b|\bno data (?:was |is )?(?:found|available|returned)\b', message, re.I)
    if missing:
        raise ProviderError('The selected source has verified events: dataProfile.sampledRows=' + str(profile['sampledRows']) +
                            '. Do not claim the source or time range has no events. Build from its verified fields, or ask one specific question about the requested metric. Zero outliers is a valid analytical outcome, not an empty source.')


def validate_blank_claim(message, document, previous, profile):
    """Do not describe a completed real-data dashboard while its canvas is blank."""
    if not profile or document != previous or document.get('visualizations') or document.get('dataSources'): return
    claimed = re.search(r'\b(?:dashboard|overview|page|chart|table|panel)\s+(?:now\s+)?(?:has|shows|contains|includes)\s+(?!(?:no|zero)\b)|\bI(?:[\u2019\']ve| have)?\s+(?:created|built|completed|added|configured)\b|^\s*(?:done|completed|created|built)\b', message, re.I)
    if claimed:
        raise ProviderError('The canvas is still blank. Return actual dashboard changes for this goal, or ask one specific question about genuinely unavailable fields or business meaning. Do not describe charts/pages that do not exist.', 422, 'blank_completion')


def presentation_message(message, prompt, repaired):
    """Keep retry mechanics in Activity unless the user asked for technical detail."""
    if not repaired or re.search(r'\b(?:explain|debug|show|why)\b[^.!?]{0,120}\b(?:SPL2?|queries|query|JSON|schema|validation|IDs?|bindings?|references?)\b', prompt, re.I):
        return message
    sentences = re.split(r'(?<=[.!?])\s+', message)
    readable = []
    for sentence in sentences:
        sentence = re.sub(r',?\s+using typed (?:absolute[- ]?)?layout actions(?: as required)?(?=[.!?]|$)', '', sentence, flags=re.I)
        if re.search(r'\b(?:supplied|provided)\b[^.!?]{0,100}\bbase\s*query\b|\bJSON Pointer\b|\b(?:validation|schema) (?:errors?|repairs?)\b|\b(?:page|panel|source|layout|visualization|object)\s+IDs?\b|\brow[- ]?link declarations?\b|\b(?:panel|binding) references?\b', sentence, re.I):
            continue
        readable.append(sentence)
    return ' '.join(readable).strip() or 'Updated your dashboard.'
