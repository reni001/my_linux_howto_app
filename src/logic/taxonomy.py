def build_taxonomy(topics):
    """
    Build category and subcategory mappings from topic list.
    """

    cat_to_icon = {}
    all_subcategories = set()
    sub_to_icon = {}
    sub_icon_global = {}

    for t in topics:
        if not isinstance(t, dict):
            continue

        cat = str(t.get("Category", "")).strip()
        sub = str(t.get("Subcategory", "")).strip().lower()

        if not cat:
            continue

        # ✅ Category icon
        if cat not in cat_to_icon:
            cat_to_icon[cat] = str(t.get("Cat_Icon", "") or "").strip()

        # ✅ Subcategory list
        if sub and sub != "nan":
            all_subcategories.add(sub)

        # ✅ Subcategory icons
        if sub and sub != "nan":
            sicon = str(t.get("Sub_Icon", "") or "").strip()

            if sicon:
                sub_icon_global.setdefault(sub, sicon)
                sub_to_icon.setdefault((cat, sub), sicon)

    return cat_to_icon, sub_to_icon, sub_icon_global, all_subcategories
