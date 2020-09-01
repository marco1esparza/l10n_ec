/*
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */
package sri;

/**
 *
 * @author ccarreno
 */
public class DevelopedSignature {
    //private static Object XAdESBESSignature;
     
    public static void main(String[] args) throws Exception {
               
    /*String xmlPath = "/tmp/test.xml";
    String pathSignature = "/tmp/test.p12";
    String passSignature = "password_p12";
    String pathOut = "/tmp/";
    String nameFileOut = "sign.xml";*/

    String pathSignature = args[0];
    String passSignature = args[1];
    String xmlPath = args[2];
    String pathOut = args[3];
    String nameFileOut = args[4];
     
    System.out.println("Ruta del XML de entrada: " + xmlPath);
    System.out.println("Ruta Certificado: " + pathSignature);
    System.out.println("Clave del Certificado: " + passSignature);
    System.out.println("Ruta de salida del XML: " + pathOut);
    System.out.println("Nombre del archivo salido: " + nameFileOut);
     
    try{
        XAdESBESSignature.firmar(xmlPath, pathSignature, passSignature, pathOut, nameFileOut);
    }catch(Exception e){
        System.out.println("Error: " + e);
    }
}
 
   
}