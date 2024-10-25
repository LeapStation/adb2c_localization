import xml.etree.ElementTree as ET
import json
import os
import argparse
from xml.dom import minidom

NAMESPACE = "http://schemas.microsoft.com/online/cpim/schemas/2013/06"

def prettify(elem):
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ").replace('<?xml version="1.0" ?>', '').strip()

def create_trust_framework_policy(translations, languages):
    root = ET.Element("TrustFrameworkPolicy", {
        "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "xmlns:xsd": "http://www.w3.org/2001/XMLSchema",
        "xmlns": NAMESPACE,
        "PolicySchemaVersion": "0.3.0.0",
        "TenantId": "mediligoacc2.onmicrosoft.com",
        "PolicyId": "B2C_1A_TrustFrameworkLocalization",
        "PublicPolicyUri": "http://mediligoacc2.onmicrosoft.com/B2C_1A_TrustFrameworkLocalization",
        "TenantObjectId": "8c890f10-c63f-4358-be89-cd18e895c6e8"
    })

    base_policy = ET.SubElement(root, "BasePolicy")
    ET.SubElement(base_policy, "TenantId").text = "mediligoacc2.onmicrosoft.com"
    ET.SubElement(base_policy, "PolicyId").text = "B2C_1A_TrustFrameworkBase"

    building_blocks = ET.SubElement(root, "BuildingBlocks")
    content_definitions = ET.SubElement(building_blocks, "ContentDefinitions")

    for content_id in translations[languages[0]]:
        content_def_el = ET.SubElement(content_definitions, "ContentDefinition", {"Id": content_id})
        localized_refs = ET.SubElement(content_def_el, "LocalizedResourcesReferences", {"MergeBehavior": "Prepend"})
        for lang in languages:
            resource_id = f"{content_id}.{lang}"
            ET.SubElement(localized_refs, "LocalizedResourcesReference", {"Language": lang, "LocalizedResourcesReferenceId": resource_id})

    localization = ET.SubElement(building_blocks, "Localization", {"Enabled": "true"})
    supported_languages = ET.SubElement(localization, "SupportedLanguages", {
        "DefaultLanguage": languages[0],  
        "MergeBehavior": "ReplaceAll"
    })

    for language in languages:
        ET.SubElement(supported_languages, "SupportedLanguage").text = language

    for lang, lang_translations in translations.items():
        for resource_id, localized_strings in lang_translations.items():
            localized_resources = ET.SubElement(localization, "LocalizedResources", {"Id": resource_id + f".{lang}"})
            localized_strings_el = ET.SubElement(localized_resources, "LocalizedStrings")

            for key, value in localized_strings.items():
                parts = key.split('.')
                if len(parts) == 5:
                    element_type, element_id, string_id = parts[2], parts[3], parts[4]
                else:
                    element_type, string_id = parts[2], parts[3]
                    element_id = None

                attributes = {"ElementType": element_type, "StringId": string_id}
                if element_id:
                    attributes["ElementId"] = element_id

                ET.SubElement(localized_strings_el, "LocalizedString", attributes).text = value

    return ET.ElementTree(root)

def json_to_xml(i18n_folder, languages, output_xml):
    translations = {}
    for lang in languages:
        with open(os.path.join(i18n_folder, f"{lang}.json"), 'r', encoding='utf-8') as f:
            translations[lang] = json.load(f)

    tree = create_trust_framework_policy(translations, languages)
    with open(output_xml, 'w', encoding='utf-8') as f:
        f.write(prettify(tree.getroot()))

def extract_content_definitions(root, language):
    content_definitions = []
    for content_def in root.findall(".//ns:ContentDefinition", {'ns': NAMESPACE}):
        content_id = content_def.get('Id')
        localized_references = []
        for ref in content_def.findall(".//ns:LocalizedResourcesReference", {'ns': NAMESPACE}):
            if ref.get("Language") == language:
                localized_references.append({
                    "Language": ref.get("Language"),
                    "LocalizedResourcesReferenceId": ref.get("LocalizedResourcesReferenceId")
                })
        if localized_references:
            content_definitions.append({"Id": content_id, "LocalizedResourcesReferences": localized_references})
    return content_definitions

def extract_translations(root, lang):
    translations = {}
    for resource in root.findall(".//ns:LocalizedResources", {'ns': NAMESPACE}):
        resource_id = resource.get('Id')
        if resource_id.endswith(f".{lang}"):
            base_resource_id = resource_id.rsplit('.', 1)[0]
            if base_resource_id not in translations:
                translations[base_resource_id] = {}
            
            for localized_string in resource.findall(".//ns:LocalizedString", {'ns': NAMESPACE}):
                element_type = localized_string.get('ElementType')
                element_id = localized_string.get('ElementId')
                string_id = localized_string.get('StringId')
                key = f"{base_resource_id}.{element_type}.{element_id}.{string_id}" if element_id else f"{base_resource_id}.{element_type}.{string_id}"
                translations[base_resource_id][key] = localized_string.text
    return translations

def generate_json_files(root, languages, output_dir):
    for lang in languages:
        translations = extract_translations(root, lang)
        translation_json_path = os.path.join(output_dir, f"{lang}.json")
        with open(translation_json_path, 'w', encoding='utf-8') as translation_file:
            json.dump(translations, translation_file, ensure_ascii=False, indent=4)

def xml_to_json(input_file, languages, i18n_folder):
    tree = ET.parse(input_file)
    root = tree.getroot()
    generate_json_files(root, languages, i18n_folder)

def main():
    parser = argparse.ArgumentParser(description='Extract and generate localization strings for Azure AD B2C')
    parser.add_argument('command', choices=['extract', 'generate'], help='Command to run')
    parser.add_argument('--languages', nargs='+', default=['en'], help='Languages to include in generation/extraction')
    parser.add_argument('--output', default='TrustFrameworkLocalization.xml', help='Output file')
    parser.add_argument('--input', default='TrustFrameworkLocalization.xml', help='Input file')
    parser.add_argument('--i18n', default='i18n', help='Folder with i18n files')

    args = parser.parse_args()

    if args.command == 'extract':
        xml_to_json(args.input, args.languages, args.i18n)
    elif args.command == 'generate':
        json_to_xml(args.i18n, args.languages, args.output)

if __name__ == '__main__':
    main()
