# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import math


UNIDADES = ( '', 'Un ', 'Dos ', 'Tres ', 'Cuatro ', 'Cinco ', 'Seis ', 'Siete ', 'Ocho ', 'Nueve ', 'Diez ', 'Once ', 'Doce ', 'Trece ', 'Catorce ', 'Quince ', 'Dieciseis ', 'Diecisiete ', 'Dieciocho ', 'Diecinueve ', 'Veinte ')
DECENAS = ('Veinti', 'Treinta ', 'Cuarenta ', 'Cincuenta ', 'Sesenta ', 'Setenta ', 'Ochenta ', 'Noventa ', 'Cien ')
CENTENAS = ('Ciento ', 'Doscientos ', 'Trescientos ', 'Cuatrocientos ', 'Quinientos ', 'Seiscientos ', 'Setecientos ', 'Ochocientos ', 'Novecientos '  )      

#TODO Se sugiere remover porque ya existe en currency
def number_to_word(number_in):
    '''
    Convierte un numero a letras
    '''
    convertido = ''
    number_str = str(number_in) if (type(number_in) != 'str') else number_in
    number_str =  number_str.zfill(9)
    millones, miles, cientos = number_str[:3], number_str[3:6], number_str[6:]
    if(millones):
        if(millones == '001'):
            convertido += 'Un Millon '
        elif(int(millones) > 0):
            convertido += '%sMillones ' % convert_number(millones)
    if(miles):
        if(miles == '001'):
            convertido += 'Mil '
        elif(int(miles) > 0):
            convertido += '%sMil ' % convert_number(miles)
    if(cientos):
        if(cientos == '001'):
            convertido += 'Un '
        elif(int(cientos) > 0):
            convertido += '%s ' % convert_number(cientos)
    return convertido

def convert_number(n):
    '''
    Obtiene número en letras según el listado.
    '''
    output = ''
    if(n == '100'):
        output = 'Cien '
    elif(n[0] != '0'):
        output = CENTENAS[int(n[0])-1]
    k = int(n[1:])
    if(k <= 20):
        output += UNIDADES[k]
    else:
        if((k > 30) & (n[2] != '0')):
            output += '%sy %s' % (DECENAS[int(n[1])-2], UNIDADES[int(n[2])])
        else:
            output += '%s%s' % (DECENAS[int(n[1])-2], UNIDADES[int(n[2])])
    return output

def l10n_ec_amount_to_words(j):
    '''
    Separa la parte entera de la fraccionaria del valor recibido
    '''
    try:   
        Arreglo1 = str(j).split(',')
        Arreglo2 = str(j).split('.')
        if (len(Arreglo1) > len(Arreglo2) or len(Arreglo1) == len(Arreglo2)):
             Arreglo = Arreglo1
        else:
            Arreglo = Arreglo2            
        if (len(Arreglo) == 2):  
            whole = math.floor(j)  
            frac = j - whole
            num = str('{0:.2f}'.format(frac))[2:]            
            return number_to_word(Arreglo[0]) + 'con ' + num + '/100'
        elif (len(Arreglo) == 1):
           return number_to_word(Arreglo[0]) + 'con ' + '00/100'
    except ValueError:
        return 'Cero'
