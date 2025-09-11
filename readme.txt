El script funciona, tiene un problema de rendimiento por el uso de memoria

Para ejecutar el script, instalar las dependencias necesarias o usar entorno virtual python

Comando para arrancar a consultar el estado del envio (hoja seguimientos) desde el inicio
python 2 script.py 

Si el proceso crasheo revisar los logs del ultimo tracking id y localizar el numero de fila donde crasheo

Ejemplo: el proceso crasheo en el idtracking 3560 correspondiente a la fila 3520, para evitar empezar desde el comienzo y retomar de donde crasheo

python 3520 script.py 
