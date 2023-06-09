# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import re
from base64 import b64encode

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from lxml import etree


class L10nEcXmlUtils():
    """Utility Methods for Ecuador's XML-related stuff."""

    NS_MAP = {"ds": "http://www.w3.org/2000/09/xmldsig#"}

    @staticmethod
    def _canonicalize_node(node, is_string=False):
        """
        Returns the canonical (C14N 1.0, without comments, non exclusive) representation of node.
        Speficied in: https://www.w3.org/TR/2001/REC-xml-c14n-20010315
        Required for computing digests and signatures.
        Returns an UTF-8 encoded bytes string.
        """
        node = etree.fromstring(node) if is_string else node
        return etree.tostring(node, method="c14n", with_comments=False, exclusive=False)

    @staticmethod
    def _cleanup_xml_content(xml_str, indent_level=0, indent=True):
        """
        Cleanups the content of the provided string representation of an XML:
        - Removes all blank text and all comments
        If indent == True, also
        - Indents all content using two spaces
        - Adds a newline as tail for proper concatenation of further elements
        Returns an etree._Element
        """
        parser = etree.XMLParser(compact=True, remove_blank_text=True, remove_comments=True)
        xml_bytes = xml_str.encode("utf-8")
        elem = etree.fromstring(xml_bytes, parser=parser)
        if indent:
            etree.indent(elem, level=indent_level)
            elem.tail = "\n"

        return elem

    @staticmethod
    def _cleanup_xml_signature(xml_sig):
        """
        Cleanups the content of the provided string representation of an XML signature
        In addition, removes all line feeds for the ds:Object element
        Returns an etree._Element
        """
        sig_elem = L10nEcXmlUtils._cleanup_xml_content(xml_sig, indent=False)
        etree.indent(sig_elem, space="")
        # Iterate over entire ds:Object sub-tree
        for elem in sig_elem.find("ds:Object", namespaces=L10nEcXmlUtils.NS_MAP).iter():
            if elem.text == "\n":
                elem.text = ""  # optional but keeps the signature object in one line
            elem.tail = ""  # necessary for some reason
        return sig_elem

    @staticmethod
    def _get_uri(uri, reference, base_uri):
        """
        Returns the content within `reference` that is identified by `uri`.
        Canonicalization is used to convert node reference to an octet stream.
        - URIs starting with # are same-document references
        https://www.w3.org/TR/xmldsig-core/#sec-URI

        - Empty URIs point to the whole document tree, without the signature
        https://www.w3.org/TR/xmldsig-core/#sec-EnvelopedSignature
        Returns an UTF-8 encoded bytes string.
        """
        node = reference.getroottree()
        if uri == base_uri:
            # Empty URI: whole document, without signature
            return L10nEcXmlUtils._canonicalize_node(
                re.sub(r"^[^\n]*<ds:Signature.*<\/ds:Signature>", r"",
                       etree.tostring(node).decode("utf-8"),
                       flags=re.DOTALL | re.MULTILINE),
                is_string=True)

        if uri.startswith("#"):
            query = "//*[@*[local-name() = '{}' ]=$uri]"
            results = node.xpath(query.format("Id"), uri=uri.lstrip("#"))  # case-sensitive 'Id'
            if len(results) == 1:
                return L10nEcXmlUtils._canonicalize_node(results[0])
            if len(results) > 1:
                raise Exception("Ambiguous reference URI {} resolved to {} nodes".format(
                    uri, len(results)))

        raise Exception('URI "' + uri + '" not found')

    @staticmethod
    def _reference_digests(node, base_uri=""):
        """
        Processes the references from node and computes their digest values as specified in
        https://www.w3.org/TR/xmldsig-core/#sec-DigestMethod
        https://www.w3.org/TR/xmldsig-core/#sec-DigestValue
        """
        for reference in node.findall("ds:Reference", namespaces=L10nEcXmlUtils.NS_MAP):
            ref_node = L10nEcXmlUtils._get_uri(reference.get("URI", ""), reference, base_uri)
            lib = hashlib.new("sha1")
            lib.update(ref_node)
            reference.find("ds:DigestValue", namespaces=L10nEcXmlUtils.NS_MAP).text = b64encode(lib.digest())

    @staticmethod
    def _fill_signature(node, private_key):
        """
        Uses private_key to sign the SignedInfo sub-node of `node`, as specified in:
        https://www.w3.org/TR/xmldsig-core/#sec-SignatureValue
        https://www.w3.org/TR/xmldsig-core/#sec-SignedInfo
        """
        signed_info_xml = node.find("ds:SignedInfo", namespaces=L10nEcXmlUtils.NS_MAP)

        # During signature generation, the digest is computed over the canonical form of the document
        signature = private_key.sign(
            L10nEcXmlUtils._canonicalize_node(signed_info_xml),
            padding.PKCS1v15(),
            hashes.SHA1()
        )
        node.find("ds:SignatureValue", namespaces=L10nEcXmlUtils.NS_MAP).text =\
            L10nEcXmlUtils._base64_print(b64encode(signature))

    @staticmethod
    def _int_to_bytes(number):
        """
        Converts an integer to an ASCII/UTF-8 byte string (with no leading zeroes).
        """
        return number.to_bytes((number.bit_length() + 7) // 8, byteorder='big')

    @staticmethod
    def _base64_print(string, length=64):
        """
        Returns the passed string modified to include a line feed every `length` characters.
        It may be recommended to keep length under 76:
        https://www.w3.org/TR/2004/REC-xmlschema-2-20041028/#rf-maxLength
        https://www.ietf.org/rfc/rfc2045.txt
        """
        string = str(string, "utf8")
        return "\n".join(
            string[pos: pos + length]
            for pos in range(0, len(string), length)
        )
