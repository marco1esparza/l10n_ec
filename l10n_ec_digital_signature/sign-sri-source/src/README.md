# Sri

Proyecto Java para la Facturación Electrónica que se usa en Ecuador, 
se basa en las especificaciones definidas en XADES_BES lo que permitiría ser 
usada en otros ambientes que requieran XADES_BES.

Original de https://github.com/joselo/sri
Compilado por TRESCLOUD Cia. Ltda, Patricio Rangles 

## Forma de usar

    XAdESBESSignature.firmar(input_file_path, key_store_path, key_store_password, output_path, out_file_name)

También.

Al compilar el código se genera un archivo sri.jar que permite firmar el documento
de la siguiente forma:

    java -jar 3CXAdESBESSSign.jar /path/sample/certificate.p12 cErTiFicAtEPaSsWoRd /path/sample/unsignedFile.xml /path/sample outputFile.xml