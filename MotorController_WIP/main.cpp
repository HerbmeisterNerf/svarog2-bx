
// This is done with platforimio. BLDC related code has been commented out.
// Include the Shield library to your Arduino project
// #include "TLE9879_Group.h"
#include "arduino.h"
#include "stdlib.h"
// Declare Shield group object
// TLE9879_Group * shields = new TLE9879_Group(1);

void setup()
{
  Serial.begin(115200);
	
	// Set the desired mode (FOC, HALL, BEMF)
	// shields->setMode(FOC);
	
	// Set the desired motor speed (RPM)
	// shields->setMotorSpeed(100);
}

void handle_command(char* command){
  // parses command and does action
  char opcode[2];
  int board_num;
  int i = 0;
  while(i<2){
    opcode[i] = command[i];
    i++;
  }
  if(strcmp(opcode,"CE")==0){
    // shields->checkErrors();
    return;
  }

  else if(strcmp(opcode,"HI")==0){
    Serial.println("Arduino says hello :)");
    return;
  }

  i++; // skip the underscore
  board_num = command[i]-'0';
  
  if(strcmp(opcode,"GS")==0){
    // shields->getMotorSpeed(board_num);
    return;
  }
  i++; // skip the underscore
  if(strcmp(opcode,"SM")==0){
    if(command[i] == '1'){
      // shields->setMotorMode(START_MOTOR, board_num);
    }
    else if(command[i] == '0'){
      // shields->setMotorMode(STOP_MOTOR, board_num);
    }
    return;
  }
  else if(strcmp(opcode,"SS")==0){
    char speed[8];
    int j = 0;
    while(command[i] != '\n'){
      speed[j] = command[i];
      j++;
      i++; 
    }
    speed[j] = '\0';
    // shields->setMotorSpeed(atoi(speed), board_num);
    return;
  }
  else if(strcmp(opcode,"SP")==0){
    char param[8];
    int j = 7;
    char val[16];
    while(command[i] != '='){
      param[j] = command[i];
      i++;
      j++;
    }
    param[j]='\0';
    i++; // skip '='
    j = 0;
    while(command[i] != '\n'){
      val[j] = command[i];
      i++;
      j++;
    }
    // shields->setParameter(atoi(param),atof(val),board_num);
  }

}

void loop()
{
  char command[256];
  Serial.readBytesUntil('\n',command,255);
  handle_command(command);
  delay(10);
}
