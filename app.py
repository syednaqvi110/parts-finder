def smart_search(query: str, df: pd.DataFrame) -> List[Tuple]:
    """Smart search that prioritizes keyword completeness - UPDATED VERSION."""
    if not query.strip() or df.empty:
        return []
    
    query = query.lower().strip()
    results = []
    
    # Split query into keywords (filter out very short words)
    query_words = set([word for word in re.split(r'[-_\s\.]+', query) if len(word) > 1])
    
    if not query_words:
        return []
    
    for idx, row in df.iterrows():
        part_num = row['part_number'].lower()
        desc_lower = row['description'].lower()
        
        # Get all words from part number and description
        part_words = set(re.split(r'[-_\s\.]+', part_num))
        desc_words = set(desc_lower.split())
        all_item_words = part_words.union(desc_words)
        
        # Count keyword matches
        matched_keywords = query_words.intersection(all_item_words)
        
        if not matched_keywords:
            continue  # No matches, skip this item
        
        # KEYWORD COMPLETENESS SCORE (most important factor)
        match_ratio = len(matched_keywords) / len(query_words)
        base_score = int(match_ratio * 100)  # 0-100 based on % of keywords matched
        
        # Bonus for part number matches (part numbers are more important than descriptions)
        part_matches = len(query_words.intersection(part_words))
        if part_matches > 0:
            base_score += 25
        
        # Additional bonuses for exact/prefix matches
        if query == part_num:
            base_score += 50  # Exact part number match
        elif query == desc_lower:
            base_score += 40  # Exact description match
        elif part_num.startswith(query):
            base_score += 30  # Part number starts with query
        elif desc_lower.startswith(query):
            base_score += 25  # Description starts with query
        elif query in part_num:
            # Substring bonus based on position (earlier = better)
            position = part_num.index(query)
            position_bonus = max(0, 20 - position)
            base_score += position_bonus
        elif query in desc_lower:
            position = desc_lower.index(query)
            position_bonus = max(0, 15 - position)
            base_score += position_bonus
        
        results.append((idx, row['part_number'], row['description'], base_score))
    
    # Sort by score (highest first) and return top results
    results.sort(key=lambda x: x[3], reverse=True)
    return results[:MAX_RESULTS]
