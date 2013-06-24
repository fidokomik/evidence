#!/usr/bin/perl
# Author: Petr Vileta, 2012
# License: WTFPL - Do What The Fuck You Want To Public License, http://sam.zoy.org/wtfpl/

use strict;
use DBI;
use CGI qw(:standard);
use CGI::Cookie;
use CGI::Carp qw(fatalsToBrowser);
use CGI ':cgi-lib';
use Unicode::Map;
use Digest::MD5 qw(md5_hex);
use LWP::UserAgent;
require HTTP::Headers;

require 'init.pl'; # mozna bude nutne doplnit path
$|=1;

our $ascii;
our $iswin=($^O=~m/Win/);
our $mapw=new Unicode::Map('CP1250');
our ($dbh,$fce,$user,$userid,@access,@grpaccess,$hipriv,$method,$logout,$adminhash);
our ($db,$dbhost,$dbport,$dbuser,$dbpw)=connect_db();

$user='';
$userid=$hipriv=0;
@access=(0,0);
@grpaccess=(0,0,0,0); #videt, leader, menit, leader
$method=lc($ENV{REQUEST_METHOD});
$fce=param('fce')*1;
$dbh = DBI->connect("DBI:mysql:$db:$dbhost:$dbport",$dbuser,$dbpw) or die "Can't connect: $DBI::errstr\n";
$dbh->do("SET character_set_connection=utf8");
$dbh->do("SET character_set_client=utf8");
$dbh->do("SET character_set_results=utf8");
$logout=get_setup('logout','number');
&login;
if($fce==1)
  {
	&jmena if(checkfunc(1));
	}
elsif($fce==2)
	{
	&vznik_clenstvi if(checkfunc(2));
	}
elsif($fce==3)
	{
	&castky if(checkfunc(3));
	}
elsif($fce==4)
	{
	&dluznici if(checkfunc(4));
	}
elsif($fce==5)
	{
	&cisluj_cleny if(checkfunc(5,'w'));
	}
elsif($fce==6)
	{
	&dokumenty_clenu if(checkfunc(6));
	}
elsif($fce==60)
	{
	&dokumenty_clenu_evid if(checkfunc(6,'w'));
	}
elsif($fce==61)
	{
	&dokumenty_clenu_novy if(param('id')*1==$userid or checkfunc(6,'w'));
	}
elsif($fce==62)
	{
	&dokumenty_clenu_zmenit if(checkfunc(6,'w'));
	}
elsif($fce==63)
	{
	&dokumenty_clenu_storno if(checkfunc(6,'w'));
	}
elsif($fce==7)
	{
	&kontakty_clenu if(checkfunc(7));
	}
elsif($fce==8)
	{
	&clenstvi if(checkfunc(8));
	}
elsif($fce==88)
	{
	&clenstvi_datum if(checkfunc(8,'w'));
	}
elsif($fce==888)
	{
	&clenstvi_zpetne if(checkfunc(8,'w'));
	}
elsif($fce==9)
	{
	&kontakty_regp if(checkfunc(9));
	}
elsif($fce==9998)
	{
	&setup_prava_aplikace if(checkfunc(9998));
	}
elsif($fce==9999)
	{
	&setup if(checkfunc(9999,'w'));
	}
else
	{
	print "<p>Sorry, zatím nefunguje</p>" if($fce > 0);
	}
print "</body></html>\n";
$dbh->disconnect;

sub kontakty_regp
{
my $idkraj=param('kraj')*1;
my $set=($idkraj==-1 ? get_setup('regp_groups','string') : $idkraj);
print	"<h2>Kontakty RegP ",ukaz_kraj($idkraj),"</h2>",
	"<form action='index.cgi' method='post'>\n",
	"<input type='hidden' name='fce' value='9'>\n";
if($method eq 'post')
	{
	my $p=get_setup('kontakty_pole','text');
	my @flds=split(/\s+/,$p);
	my $query='';
	my (@pole,@field);
	foreach my $p(@flds)
		{
		my ($n,$f)=split(/=/,$p);
		$query.="`$f`,";
		push @pole,$n;
		push @field,$f;
		}
#	$query=~s/,$//;
	$query.="`username_clean`";
	my $sth1=$dbh->prepare("SELECT $query FROM `phpbb_users`
		LEFT JOIN `phpbb_profile_fields_data`
			ON(`phpbb_profile_fields_data`.`user_id`=`phpbb_users`.`user_id`)
		WHERE `phpbb_users`.`user_id`=?");
	my $sth=$dbh->prepare("SELECT `phpbb_users`.`user_id`,`username`,
				`pf_fullname`,`group_name`,`user_regdate`,`username_clean`
		FROM `phpbb_user_group`
		LEFT JOIN `phpbb_users`
			ON(`phpbb_users`.`user_id`=`phpbb_user_group`.`user_id`)
		LEFT JOIN `phpbb_groups`
				ON(`phpbb_groups`.`group_id`=`phpbb_user_group`.`group_id`)
		LEFT JOIN `phpbb_profile_fields_data`
			ON(`phpbb_profile_fields_data`.`user_id`=`phpbb_users`.`user_id`)
		WHERE FIND_IN_SET(`phpbb_user_group`.`group_id`,'$set')
		ORDER BY 4,6");
	$sth->execute() or die $sth->errstr;
	my ($id,$username,$fullname,$group,$datumreg,$lcname);
	$sth->bind_columns(\($id,$username,$fullname,$group,$datumreg,$lcname));
	print	"<input type='hidden' name='kraj' value='$idkraj'>\n",
		"<table><caption class='norm'>",$sth->rows," členů</caption>\n",
		"<tr class='hdr'><td>Registrace</td><td>RegP</td><td>Plné jméno</td>",
		"<td colspan=2>Kontakty a další informace</td>",
		($set=~m/,/ ? "<td>Kraj</td>" : ''),
		"</tr>\n";
	my $span=$#pole + 1;
	while($sth->fetch)
		{
		$group=~s/^regp\s+//i;
		my @dat=(localtime($datumreg))[3,4,5];
		my $d=sprintf("%02d.%02d.%04d",$dat[0],$dat[1]+1,$dat[2]+1900);
		print	"<tr><td class='ri' rowspan=$span>$d</td>",
			"<td class='nowrap' rowspan=$span>$username</td>",
			"<td class='nowrap' rowspan=$span>$fullname</td>";
		$sth1->execute($id) or die $sth1->errstr;
		my $row=$sth1->fetchrow_arrayref;
		$sth1->finish;
		print	"<td>$pole[0]</td>",
			"<td>",$row->[0],"</td>",
			($set=~m/,/ ? "<td rowspan=$span>$group</td>" : ''),
			"</tr>\n";
		for($p=1;$p<=$#pole;$p++)
			{
			print	"<tr><td>$pole[$p]</td><td>";
			if($row->[$p])
				{
				if($field[$p] eq 'user_email')
					{
					my $m=$row->[$p];
#					($m=$row->[$#pole + 1])=~s/^(\S+)\s+(\S+)$/$1.$2\@ceskapiratskastrana.cz/;
					print "<a href='mailto:$m'>$m</a>";
					}
				elsif($field[$p] eq 'user_website')
					{
					my ($w,$w1);
					$w=$row->[$p];
					$w=~s/^\s+|\s+$//g;
					$w=~s/^(\S+)\s+.+$/$1/;
					$w='http://' . $w unless($w=~m/^https*:\/\//);
					($w1=$w)=~s/^https*:\/\/(.+)$/$1/;
					print "<a href='$w' target='_blank'>$w1</a>";
					}
				else
					{
					print $row->[$p];
					}
				}
			else
				{
				print '&nbsp;';
				}
			print "</td></tr>";
			}
		}
	$sth->finish;
	print "</table><p>&nbsp;</p>";
	}
else
	{
	print "<p>";
	if($access[0] or $access[1] or $hipriv)
		{
		&regpkraje(0);
		}
	elsif($grpaccess[0] or $grpaccess[2])
		{
		&regpkraje((krajregp())[1]);
		}
	print	"&nbsp;&nbsp;<input type='submit' value='Zobrazit'></p>\n";
	}
print	"</form>\n";
}

sub clenstvi_zpetne
{
my $forumgroup=get_setup('maingroup','number');
my $skupina=param('skupina')*1;
my $set=($skupina==0 ? get_setup('groups_to_log','text') : $skupina);
my $uziv=param('uziv')*1;
my $od=param('datumod');
my $do=param('datumdo');
my $clen=param('clen')*1;
my $vedouci=1*(lc(param('vedouci')) eq 'on');
my $funkce=1*(lc(param('funkce')) eq 'on');
my $err='';
if($method eq 'post')
	{
	my ($datod,$datdo)=(0,0);
	if(length($od) > 0)
		{
		$od=~s/[^\.,\d]//g;
		if($od=~m/^(\d{1,2}).(\d{1,2}).(\d{4})/)
			{
			$datod=sprintf('%04d%02d%02d',$3,$2,$1);
			}
		}
	if(length($do) > 0)
		{
		$do=~s/[^\.,\d]//g;
		if($do=~m/^(\d{1,2}).(\d{1,2}).(\d{4})/)
			{
			$datdo=sprintf('%04d%02d%02d',$3,$2,$1);
			}
		}
	if($clen==0)
		{
		$err='Vyber osobu!';
		}
	elsif($datod==0)
		{
		$err="Zapiš datum 'V období od'!";
		}
	elsif($datdo==0)
		{
		$err="Zapiš datum 'V období do'!";
		}
	else
		{
		my $ok=1;
		my $sth=$dbh->prepare("INSERT INTO `evidence_clenstvi` SET
				`user_id`=?,
				`group_id`=?,
				`vedouci`=?,
				`funkce`=?,
				`datum_od`=?,
				`datum_do`=?");
		$sth->execute($clen,$skupina,$vedouci,$funkce,$datod,$datdo) or $ok=0;
		$sth->finish;
		unless($ok)
			{
			$err='Totožný zápis již existuje';
			}
		else
			{
			$fce=8;
			my $g=ukaz_skupinu($skupina);
			$g=~s/^.+?\-\s(.+)$/$1/s;
			my $t="EVIDENCE: Doplňen historický záznam o členovi '#' ve skupině '$g'\nVedoucí: "
					. ($vedouci ? 'ANO' : 'NE') . "\nFunkce: "
					. ($funkce ? 'ANO' : 'NE') . "\nPro období: $od až $do";
			&log_it($userid,$clen,$t);
			&clenstvi;
			return;
			}
		}
	}
print	"<h2>Členství ve skupinách",ukaz_skupinu($skupina);
if($od or $do)
	{
	print "&nbsp;&nbsp;<small><small class='norm'>V období od <b>",(($od) ? $od : '?'),'</b> do <b>',(($do) ? $do : 'dosud'),"</b></small></small>";
	}
print	"<br><span class='red'>Zpětný zápis</span></h2>",
	"<form action='index.cgi' method='post'>\n",
	"<input type='hidden' name='fce' value='888'>",
	"<input type='hidden' name='skupina' value=$skupina>",
	"<input type='hidden' name='user' value=$uziv>",
	"\n<p>",
	($err ? "<h2 class='bgred'>POZOR: $err</h2>" : ''),
	"Osoba:&nbsp;<select name='clen' size=1>\n",
	"<option value=0 style='background-color:#cccccc !important'",
	($clen==0 ? ' selected' : ''),
	">vyber osobu</option>\n";
my ($userid,$name,$fullname,$grp);
my $sth=$dbh->prepare("SELECT `phpbb_users`.`user_id`,`username_clean`,`pf_fullname`,
			`phpbb_user_group`.`group_id`
		FROM `phpbb_users`
		LEFT JOIN `phpbb_profile_fields_data` ON (`phpbb_profile_fields_data`.`user_id`=`phpbb_users`.`user_id`)
		LEFT JOIN `phpbb_user_group` ON (`phpbb_users`.`user_id`=`phpbb_user_group`.`user_id`
			AND `phpbb_user_group`.`group_id`=$forumgroup)
		WHERE `user_type`!=2
		ORDER BY `username_clean`");
$sth->execute() or die $sth->errstr;
$sth->bind_columns(\($userid,$name,$fullname,$grp));
while ($sth->fetch)
	{
	print	"<option value=$userid",($grp==$forumgroup ? " style='background-color:#99ff99 !important'" : ''),
		($clen==$userid ? ' selected' : ''),
		">$name",($fullname ? " \($fullname\)" : ''),
		"</option>\n";
	}
$sth->finish;
print	"</select>\n<i>(současní členové označeni zeleně)</i>";
print	"<br><input type='checkbox' name='vedouci'",
	($vedouci ? ' checked' : ''),">předseda nebo vedoucí",
	"<br><input type='checkbox' name='funkce'",
	($funkce ? ' checked' : ''),">místopředseda nebo jiná funkce",
	"<br>V období od:<input type='text' name='datumod'",
	($od ? " value='$od'" : ''),
	" maxlength=10 style='width: 6em'> <i>formát DD.MM.RRRR</i>",
	"<br>V období do:<input type='text' name='datumdo'",
	($do ? " value='$do'" : ''),
	" maxlength=10 style='width: 6em'> <i>formát DD.MM.RRRR</i>",
	"<br><input type='submit' value='Zapsat'></p></form>\n";
}

sub clenstvi_datum
{
my $skupina=param('skupina')*1;
my $userid=param('uziv')*1;
my $ved=param('v')*1;
my $fun=param('f')*1;
my $sth;
if($method eq 'post')
	{
	my $od=param('dat');
	if(length($od) > 0)
		{
		$od=~s/[^\.,\d]//g;
		if($od=~m/^(\d{1,2}).(\d{1,2}).(\d{4})/)
			{
			my $datum=sprintf('%04d%02d%02d',$3,$2,$1);
			$sth=$dbh->prepare("UPDATE `evidence_clenstvi` SET
					`datum_od`=?
				WHERE `user_id`=? AND `group_id`=?
					AND `vedouci`=? and `funkce`=?");
			$sth->execute($datum,$userid,$skupina,$ved,$fun) or die $sth->errstr;
			$sth->finish;
			$fce=8;
			&clenstvi;
			return;
			}
		}
	}
$sth=$dbh->prepare("SELECT `pf_fullname` FROM `phpbb_profile_fields_data`
		WHERE `user_id`=?");
$sth->execute($userid) or die $sth->errstr;
my ($username)=$sth->fetchrow_array();
$sth->finish;
print	"<h2>Členství ve skupinách",ukaz_skupinu($skupina),
	" - $username</h2>";
print	"<form action='index.cgi#u$userid' method='post'>\n",
	"<input type='hidden' name='fce' value='88'>\n",
	"<input type='hidden' name='skupina' value='$skupina'>\n",
	"<input type='hidden' name='uziv' value='$userid'>\n",
	"<input type='hidden' name='v' value='$ved'>\n",
	"<input type='hidden' name='f' value='$fun'>\n";
print	"Datum od:<input type='text' name='dat' maxlength=10 style='width: 6em'>",
	"&nbsp;&nbsp;<input type='submit' value='Uložit'></p>\n",
	"</form>\n";
}

sub clenstvi
{
my $forumgroup=get_setup('maingroup','number');
my $skupina=param('skupina')*1;
my $set=($skupina==0 ? get_setup('groups_to_log','text') : $skupina);
my $od=param('datumod');
my $do=param('datumdo');
print	"<h2>Členství ve skupinách",ukaz_skupinu($skupina);
if($od or $do)
	{
	print "&nbsp;&nbsp;<small><small class='norm'>V období od <b>",(($od) ? $od : '?'),'</b> do <b>',(($do) ? $do : 'dosud'),"</b></small></small>";
	}
print	"</h2>";
#if($method eq 'post' or param('skupina'))
if($method eq 'post')
	{
	my $where='';
	if(length($do) > 0)
		{
		$do=~s/[^\.,\d]//g;
		}
	if(length($od) > 0)
		{
		$od=~s/[^\.,\d]//g;
		}
	if(length($od) > 0 and length($do) > 0)
		{
		if($od=~m/^(\d{1,2}).(\d{1,2}).(\d{4})/)
			{
			$where.=" AND `datum_od` <= " . sprintf('%04d%02d%02d',$3,$2,$1);
			}
		if($do=~m/^(\d{1,2}).(\d{1,2}).(\d{4})/)
			{
			$where.=" AND (ISNULL(`datum_do`) OR `datum_do` >= " . sprintf('%04d%02d%02d',$3,$2,$1) . ')';
			}
		}
	elsif(length($od) > 0)
		{
		if($od=~m/^(\d{1,2}).(\d{1,2}).(\d{4})/)
			{
			$where.=" AND `datum_od` >= " . sprintf('%04d%02d%02d',$3,$2,$1);
			}
		}
	elsif(length($do) > 0)
		{
		if($do=~m/^(\d{1,2}).(\d{1,2}).(\d{4})/)
			{
			$where.=" AND (ISNULL(`datum_do`) OR `datum_do` <= " . sprintf('%04d%02d%02d',$3,$2,$1) . ')';
			}
		}
	my ($sth,$userid,$groupid,$vedouci,$funkce,$profese,$fullname,$username,$address,$avatar,$datumod,$datumdo,$out,$regp);
	$sth=$dbh->prepare("SELECT `evidence_clenstvi`.`user_id`,
			`evidence_clenstvi`.`group_id`,
			`vedouci`,`funkce`,`pf_profese`,`pf_fullname`,`username`,`user_from`,`user_avatar`,
			DATE_FORMAT(`datum_od`,'%d.%m.%Y'),
			DATE_FORMAT(`datum_do`,'%d.%m.%Y'),NOT ISNULL(`datum_do`) AS `out`,
			ISNULL(`phpbb_user_group`.`group_id`) AS `regp`
		FROM `evidence_clenstvi`
		LEFT JOIN `phpbb_users`
			ON (`evidence_clenstvi`.`user_id`=`phpbb_users`.`user_id`)
		LEFT JOIN `phpbb_profile_fields_data`
			ON (`evidence_clenstvi`.`user_id`=`phpbb_profile_fields_data`.`user_id`)
		LEFT JOIN `phpbb_user_group`
			ON (`phpbb_user_group`.`user_id`=`evidence_clenstvi`.`user_id` AND `phpbb_user_group`.`group_id`=$forumgroup)
		WHERE `evidence_clenstvi`.`group_id`=? $where
		ORDER BY `out`,`vedouci` DESC,`funkce` DESC,`username`");
	$sth->execute($skupina) or die $sth->errstr;
	$sth->bind_columns(\($userid,$groupid,$vedouci,$funkce,$profese,$fullname,$username,$address,$avatar,$datumod,$datumdo,$out,$regp));
	print	"<p>Členů: ",$sth->rows,"</p>\n<table>";
	while ($sth->fetch)
		{
		$fullname=~s/^\s+|\s+$//g;
		my $image='&nbsp;';
		if($avatar=~m#:\/\/#)
			{
			$image="<img class='avatar' src='$avatar'>";
			}
		elsif($avatar)
			{
			$image="<img class='avatar' src='http://www.ceskapiratskastrana.cz/forum/download/file.php?avatar=$avatar'>";
			}
		print	"<tr",($out ? " style='background: #cccccc'" : ''),
			"><td>$image</td><td>";
		if($vedouci) {print "<big style='font-size: 150%'><b>";}
		elsif($funkce) {print '<b>';}
		print ''.(length($fullname)>0 ? $fullname : $username);
		if($vedouci) {print '</b></big>';}
		elsif($funkce) {print '</b>';}
		print	"<br>&nbsp;<br>$profese<br>$address",
			"</td><td><a name='u$userid'";
		unless($groupid==$forumgroup)
			{
			print	" href='index.cgi?fce=88&skupina=$skupina&uziv=$userid",
				"&v=$vedouci&f=$funkce&datumod=$od&datumdo=$do'",
				" title='Změnit datum'";
			}
		print	'>',($datumod=~m/^00/ ? '?'x10 : $datumod),'</a>',
			' - ',($out==0 ? 'dosud' : $datumdo),
			($regp ? "<br><br><b>RegP</b>" : ''),
			'</td>';
		print "</tr>\n";
		}
	print "</table>";
	$sth->finish;
	print	"<p><a href='index.cgi?fce=888&skupina=$skupina&uziv=$userid&datumod=$od&datumdo=$do'>",
		"Zápis za předchozí období</a></p>";
	}
else
	{
	print	"<form action='index.cgi' method='post'>\n",
		"<input type='hidden' name='fce' value='8'>\n<p>";
	if($access[0] or $access[1] or $hipriv or $grpaccess[2]==$forumgroup)
		{
		&skupiny(0);
		}
	elsif($grpaccess[0] or $grpaccess[2])
		{
		# ???
		&skupiny((krajclena())[1]);
		}
	print	"<br>Za období od:<input type='text' name='datumod' maxlength=10 style='width: 6em'> <i>formát DD.MM.RRRR nebo nechte prázdné</i>",
		"<br>Za období do:<input type='text' name='datumdo' maxlength=10 style='width: 6em'> <i>formát DD.MM.RRRR nebo nechte prázdné</i>",
		"<br><input type='submit' value='Zobrazit'></p></form>\n";
	}
}

sub kontakty_clenu
{
my $idkraj=param('kraj')*1;
my $set=($idkraj==-1 ? get_setup('ksgroups','string') : $idkraj);
print	"<h2>Kontakty členů ",ukaz_kraj($idkraj),"</h2>",
	"<form action='index.cgi' method='post'>\n",
	"<input type='hidden' name='fce' value='7'>\n";
if($method eq 'post')
	{
	my $p=get_setup('kontakty_pole','text');
	my @flds=split(/\s+/,$p);
	my $query='';
	my (@pole,@field);
	foreach my $p(@flds)
		{
		my ($n,$f)=split(/=/,$p);
		$query.="`$f`,";
		push @pole,$n;
		push @field,$f;
		}
#	$query=~s/,$//;
	$query.="`username_clean`";
	my $sth1=$dbh->prepare("SELECT $query FROM `phpbb_users`
		LEFT JOIN `phpbb_profile_fields_data`
			ON(`phpbb_profile_fields_data`.`user_id`=`phpbb_users`.`user_id`)
		WHERE `phpbb_users`.`user_id`=?");
	my $sth=$dbh->prepare("SELECT `phpbb_users`.`user_id`,`username`,
				`pf_fullname`,`group_name`,`pf_idclena`
		FROM `phpbb_user_group`
		LEFT JOIN `phpbb_users`
			ON(`phpbb_users`.`user_id`=`phpbb_user_group`.`user_id`)
		LEFT JOIN `phpbb_groups`
				ON(`phpbb_groups`.`group_id`=`phpbb_user_group`.`group_id`)
		LEFT JOIN `phpbb_profile_fields_data`
			ON(`phpbb_profile_fields_data`.`user_id`=`phpbb_users`.`user_id`)
		WHERE FIND_IN_SET(`phpbb_user_group`.`group_id`,'$set')
		ORDER BY 4,2");
	$sth->execute() or die $sth->errstr;
	my ($id,$username,$fullname,$group,$idclena);
	$sth->bind_columns(\($id,$username,$fullname,$group,$idclena));
	print	"<input type='hidden' name='kraj' value='$idkraj'>\n",
		"<table><caption class='norm'>",$sth->rows," členů</caption>\n",
		"<tr class='hdr'><td>Číslo</td><td>Člen</td><td>Plné jméno</td>",
		"<td colspan=2>Kontakty a další informace</td>",
		($set=~m/,/ ? "<td>Kraj</td>" : ''),
		"</tr>\n";
	my $span=$#pole + 1;
	while($sth->fetch)
		{
		print	"<tr><td class='ri' rowspan=$span>$idclena</td>",
			"<td class='nowrap' rowspan=$span>$username</td>",
			"<td class='nowrap' rowspan=$span>$fullname</td>";
		$sth1->execute($id) or die $sth1->errstr;
		my $row=$sth1->fetchrow_arrayref;
		$sth1->finish;
		print	"<td>$pole[0]</td>",
			"<td>",$row->[0],"</td>",
			($set=~m/,/ ? "<td rowspan=$span>$group</td>" : ''),
			"</tr>\n";
		for($p=1;$p<=$#pole;$p++)
			{
			print	"<tr><td>$pole[$p]</td><td>";
			if($row->[$p])
				{
				if($field[$p] eq 'user_email')
					{
					my $m;
					($m=$row->[$#pole + 1])=~s/^(\S+)\s+(\S+)$/$1.$2\@ceskapiratskastrana.cz/;
					print "<a href='mailto:$m'>$m</a>";
					}
				elsif($field[$p] eq 'user_website')
					{
					my ($w,$w1);
					$w=$row->[$p];
					$w=~s/^\s+|\s+$//g;
					$w=~s/^(\S+)\s+.+$/$1/;
					$w='http://' . $w unless($w=~m/^https*:\/\//);
					($w1=$w)=~s/^https*:\/\/(.+)$/$1/;
					print "<a href='$w' target='_blank'>$w1</a>";
					}
				else
					{
					print $row->[$p];
					}
				}
			else
				{
				print '&nbsp;';
				}
			print "</td></tr>";
			}
		}
	$sth->finish;
	print "</table><p>&nbsp;</p>";
	}
else
	{
	print "<p>";
	if($access[0] or $access[1] or $hipriv)
		{
		&kraje(0);
		}
	elsif($grpaccess[0] or $grpaccess[2])
		{
		&kraje((krajclena())[1]);
		}
	print	"&nbsp;&nbsp;<input type='submit' value='Zobrazit'></p>\n";
	}
print	"</form>\n";
}

sub dokumenty_clenu_archivuj
{
my ($fname,$fext,$fileid,$usr,$path)=@_;
my ($oldname,$rename);
my $sth=$dbh->prepare("select `soubor` from `evidence_dokumenty`
		where soubor like '$fname%' and `user_id`=?");
$sth->execute($usr) or die $sth->errstr;
$sth->bind_columns(\($oldname));
my $max=0;
while ($sth->fetch)
	{
	$oldname=~s/^.+\((\d+)\).+$/$1/;
	$max=$oldname if($oldname > $max);
	}
$max++;
$sth=$dbh->prepare("select `soubor` from `evidence_dokumenty` where `id`=?");
$sth->execute($fileid) or die $sth->errstr;
$sth->bind_columns(\($oldname));
my $ok=1;
$sth->fetch;
$sth->finish;
if($oldname=~m/^(.+)(\..*)$/)
	{
	my ($f,$e)=($1,$2);
	$rename="$f($max)$e";
	if(-e "$path$rename")
		{
		$ok=0;
		}
	else
		{
		rename "$path$f$e","$path$rename" or $ok=0;
		}
	}
else
	{
	$rename="$oldname($max)";
	if(-e "$path$rename")
		{
		$ok=0;
		}
	else
		{
		rename "$path$oldname","$path$rename" or $ok=0;
		}
	}
return 0 unless($ok);
$sth=$dbh->prepare("update `evidence_dokumenty` set
			`soubor`=?,
			`aktualizoval`=?,
			`aktualizace`=now()
		where `id`=?");
$sth->execute($rename,"$user;$userid",$fileid) or $ok=0;
$sth->finish;
return $ok;
}

sub dokumenty_clenu_zmenit
{
my $mainpath=get_setup('data_path','string');
$mainpath=~s#\/+$##;
my $ext1=get_setup('dokumenty_prihlaska_ext','string');
my $ext2=get_setup('dokumenty_avatar_ext','string');
my $ext3=get_setup('dokumenty_foto_ext','string');
my $ext4=get_setup('dokumenty_jine_verejne_ext','string');
my $ext5=get_setup('dokumenty_jine_neverejne_ext','string');
my $idkraj=param('kraj')*1;
my $id=param('id')*1;
my $file=param('file')*1;
my $newname=lecit(param('newname')) || '';
my $newfile=lecit(param('newfile'));
my $error='';
my $aogroup=get_setup('ao_group','number');
my ($gid,$gname,$uname,$soubor,$filetype,$videt,$menit);
my $sth=$dbh->prepare("select `pf_fullname` from `phpbb_profile_fields_data`
		where `user_id`=?");
$sth->execute($id) or die $sth->errstr;
$sth->bind_columns(\($uname));
$sth->fetch;
$sth=$dbh->prepare("select `soubor`,`druh`,`smi_cist`,`smi_menit` from `evidence_dokumenty`
		where `id`=?");
$sth->execute($file) or die $sth->errstr;
$sth->bind_columns(\($soubor,$filetype,$videt,$menit));
$sth->fetch;
$sth->finish;
my %prava;
if(defined Vars->{acr_1})
	{
	%prava->{'1'}->{videt}=param('acr_1');
	}
if(defined Vars->{acw_1})
	{
	%prava->{'1'}->{menit}=param('acw_1');
	}
%prava->{'1'}->{popis}="Soubor uživatele '$uname'";
if($method eq 'post')
	{
	if(param('cur_1'))
		{
		vyber_clena("- uživatelé s přístupem pro čtení",'r',1,%prava);
		return;		}
	elsif(param('cuw_1'))
		{
		vyber_clena("- uživatelé s přístupem pro zápis",'w',1,%prava);
		return;
		}
	elsif(param('cgr_1'))
		{
		vyber_skupinu("- skupiny s přístupem pro čtení",'r',1,%prava);
		return;		}
	elsif(param('cgw_1'))
		{
		vyber_skupinu("- skupiny s přístupem pro zápis",'w',1,%prava);
		return;
		}
	elsif(param('vyber'))
		{
		my @pars=param();
		foreach my $p(@pars)
			{
			if(substr($p,0,4) eq 'usr_')
				{
				$p=~m/^\D+_(\d+)$/;
				my $u=$1;
				if(param('access') eq 'r')
					{
					%prava->{'1'}->{videt}="U$u," . %prava->{'1'}->{videt};
					}
				}
			elsif(substr($p,0,4) eq 'usw_')
				{
				$p=~m/^\D+_(\d+)$/;
				my $u=$1;
				if(param('access') eq 'w')
					{
					%prava->{'1'}->{menit}="U$u," . %prava->{'1'}->{menit};
					}
				}
			elsif(substr($p,0,4) eq 'gnr_')
				{
				$p=~m/^\D+_(\d+)$/;
				my $g=$1;
				if(param('access') eq 'r')
					{
					if(param("glr_$g"))
						{
						%prava->{'1'}->{videt}=%prava->{'1'}->{videt} . ",G$g" . 'L';
						}
					else
						{
						%prava->{'1'}->{videt}=%prava->{'1'}->{videt} . ",G$g";
						}
					}
				}
			elsif(substr($p,0,4) eq 'gnw_')
				{
				$p=~m/^\D+_(\d+)$/;
				my $g=$1;
				if(param('access') eq 'w')
					{
					if(param("glw_$g"))
						{
						%prava->{'1'}->{menit}=%prava->{'1'}->{menit} . ",G$g" . 'L';
						}
					else
						{
						%prava->{'1'}->{menit}=%prava->{'1'}->{menit} . ",G$g";
						}
					}
				}
			}
		%prava->{'1'}->{videt}=~s/,+/,/sg;
		%prava->{'1'}->{videt}=~s/^,|,$//sg;
		%prava->{'1'}->{videt}=~s/(\d|L)(U|G)/$1,$2/sg;
		%prava->{'1'}->{menit}=~s/^,|,$//sg;
		%prava->{'1'}->{menit}=~s/,+/,/sg;
		%prava->{'1'}->{menit}=~s/(\d|L)(U|G)/$1,$2/sg;
		}
	else
		{
		$newfile=~s/[\r\n]//sg;
		my $ext='';
		if($newfile=~m/^.+\.(.+)$/)
			{
			$ext=lc($1);
			}
		if(! $newfile)
			{
			my $sth=$dbh->prepare("update `evidence_dokumenty` set
						`smi_cist`=?,
						`smi_menit`=?
					where `id`=?");
			$sth->execute(%prava->{'1'}->{videt},%prava->{'1'}->{menit},$file) or $error="Chyba databáze: " . $sth->errstr;
			if($error)
				{
				$sth->finish;
				$dbh->do("unlock tables");
				goto DCZ ;
				}
			$sth->finish;
			$dbh->do("unlock tables");
			print "<b>Uloženo</b> (id=$file)";
			param('fce',6);
			&dokumenty_clenu;
			return;
			}
		elsif($filetype*1 < 1 or $filetype*1 > 4)
			{
			$error="Nebyl vybrán typ soubor.";
			goto DCZ;
			}
		elsif($filetype==1 and ! 1*(",$ext1,")=~m/,$ext,/)
			{
			$error="Nepovolený typ souboru 'přihláška'.";
			goto DCZ;
			}
		elsif($filetype==2 and ! 1*(",$ext2,")=~m/,$ext,/)
			{
			$error="Nepovolený typ souboru 'avatar'.";
			goto DCZ;
			}
		elsif($filetype==3 and ! 1*(",$ext3,")=~m/,$ext,/)
			{
			$error="Nepovolený typ souboru 'foto'.";
			goto DCZ;
			}
		elsif($filetype==4 and ! 1*(",$ext4,")=~m/,$ext,/)
			{
			$error="Nepovolený typ souboru 'jiný veřejný'.";
			goto DCZ;
			}
		elsif($filetype==5 and ! 1*(",$ext5,")=~m/,$ext,/)
			{
			$error="Nepovolený typ souboru 'jiný soukromý'.";
			goto DCZ;
			}
		my $filename=lc($newfile);
		$filename=~s#\\#/#g;
		$filename=~s#^.+/(.+)$#$1#;
		if($filetype > 3 and length($newname) > 0)
			{
			unless(is_ascii($newname))
				{
				$error="Nepovolené znaky v názvu souboru. $filetype";
				goto DCZ;
				}
			$filename=~s/^(.+)(\..*)$/$1/;
			$filename="$newname$2";
			}
		elsif($filetype > 3 and ! is_ascii($filename))
			{
			$error="Nepovolené znaky v názvu souboru.";
			($newname=$filename)=~s/^(.+)\..*$/$1/;
			goto DCZ;
			}
		my $path;
		if($filetype > 1 and $filetype < 5)
			{
			$path="$mainpath/public";
			unless(-d $path)
				{
				mkdir $path or $error="Nelze vytvořit adresář '$path'";
				goto DCZ if($error);
				}
			$path="$mainpath/public/$id/";
			}
		else
			{
			$path="$mainpath/$id/";
			}
		unless(-d $path)
			{
			mkdir $path or $error="Nelze vytvořit adresář uživatele '$path'";
			}
		goto DCZ if($error);
		$dbh->do("lock tables `evidence_dokumenty` write");
		if($filetype==1)
			{
			$filename="prihlaska.$ext";
			unless(dokumenty_clenu_archivuj('prihlaska',$ext,$file,$id,$path))
				{
				$error="Nepodařilo se archivovat předchozí přihlášku člena";
				$dbh->do("unlock tables");
				goto DCZ;
				}
			}
		elsif($filetype==2)
			{
			$filename="avatar.$ext";
			unless(dokumenty_clenu_archivuj('avatar',$ext,$file,$id,$path))
				{
				$error="Nepodařilo se archivovat předchozí avatar člena";
				$dbh->do("unlock tables");
				goto DCZ;
				}
			}
		elsif($filetype==3)
			{
			$filename="foto.$ext";
			unless(dokumenty_clenu_archivuj('foto',$ext,$file,$id,$path))
				{
				$error="Nepodařilo se archivovat předchozí foto člena";
				$dbh->do("unlock tables");
				goto DCZ;
				}
			}
		else
			{
			($newname=$filename)=~s/^(.+)\..*$/$1/;
			unless(dokumenty_clenu_archivuj($newname,$ext,$file,$id,$path))
				{
				$error="Nepodařilo se archivovat předchozí soubor člena";
				$dbh->do("unlock tables");
				goto DCZ;
				}
			}
		open O,"> $path$filename" or $error="Nelze vytvořit soubor '$path$filename'";
		goto DCZ if($error);
		binmode O;
		while(<$newfile>)
			{
			print O $_ or $error="Chyba při zápisu do souboru '$path$filename'";
			}
		close O;
		if($error)
			{
			$dbh->do("unlock tables");
			goto DCZ;
			}
		my $sth=$dbh->prepare("insert into `evidence_dokumenty` set
					`user_id`=?,
					`soubor`=?,
					`vlozeno`=now(),
					`vlozil`=?,
					`smi_cist`=?,
					`smi_menit`=?,
					`druh`=?");
		$sth->execute($id,$filename,"$user;$userid",%prava->{'1'}->{videt},%prava->{'1'}->{menit},$filetype) or $error="Chyba databáze: " . $sth->errstr;
		if($error)
			{
			$sth->finish;
			$dbh->do("unlock tables");
			goto DCZ ;
			}
		$sth=$dbh->prepare("select last_insert_id()");
		$sth->execute() or $error="Nelze uložit do databáze. ERROR: " . $sth->errstr;
		my ($fid)=$sth->fetchrow_array();
		$sth->finish;
		$dbh->do("unlock tables");
		print "<b>Uloženo</b> (id=$fid)";
		param('fce',6);
		&dokumenty_clenu;
		return;
		}
	}
else
	{
	%prava->{'1'}->{videt}=$videt;
	%prava->{'1'}->{menit}=$menit;
	}
DCZ:
print	"<h2>Evidence dokumentů členů",ukaz_kraj($idkraj),"</h2>\n";
print	"<p>Aktualizace dokumentu pro <b>$uname</b></p>\n",
	"<form action='index.cgi#a$id' method='post' enctype='multipart/form-data'>",
	"<input type='hidden' name='fce' value=$fce>",
	"<input type='hidden' name='kraj' value=$idkraj>",
	"<input type='hidden' name='id' value=$id>",
	"<input type='hidden' name='file' value=$file>",
	"<input type='hidden' name='acr_1' value='",%prava->{'1'}->{videt},"'>",
	"<input type='hidden' name='acw_1' value='",%prava->{'1'}->{menit},"'>",
	"<table>\n";
if($error)
	{
	print "<caption>$error</caption>\n";
	}
print	"<tr><td>Soubor</td><td><input name='newfile' type='file'></td></tr>\n",
	"<tr><td>Typ souboru</td><td>";
if($filetype==1) {print "<b>přihláška</b> <i>(povoleno: $ext1)</i>"}
elsif($filetype==2) {print "<b>avatar</b> <i>(povoleno: $ext2)</i>"}
elsif($filetype==3) {print "<b>foto</b> <i>(povoleno: $ext3)</i>"}
elsif($filetype==4) {print "<b>jiný veřejný</b> <i>(povoleno: $ext4)</i>"}
elsif($filetype==5) {print "<b>jiný neveřejný</b> <i>(povoleno: $ext5)</i>"}
if($filetype > 3)
	{
	print 	"<br>Jméno souboru:&nbsp;<input id='filename' name='filename' type='text' value='$newname' maxlenght=255",
		"> <i>(bez diakritiky, mezer a přípony)</i>";
	}
print	"</td></tr>\n",
	"<tr><td>Smí vidět</td><td><div style='height: 12em; overflow-y: scroll; overflow-x: show; white-space: nowrap; margin: 0.2em 0 0.2em 0; width: 20em;'>";
	showusers('U',%prava->{'1'}->{videt});
	showusers('G',%prava->{'1'}->{videt});
print	"</div><input type='submit' name='cur_1' value='Členové'>",
	"&nbsp;&nbsp;<input type='submit' name='cgr_1' value='Skupiny'>",
	"</td></tr>",
	"<tr><td>Smí měnit</td><td><div style='height: 12em; overflow-y: scroll; overflow-x: show; white-space: nowrap; margin: 0.2em 0 0.2em 0; width: 20em;'>";
	showusers('U',%prava->{'1'}->{menit});
	showusers('G',%prava->{'1'}->{menit});
print	"</div><input type='submit' name='cuw_1' value='Členové'>",
	"&nbsp;&nbsp;<input type='submit' name='cgw_1' value='Skupiny'>",
	"</td></tr>",
	"<tr><th colspan=2><input class='bold' type='submit' name='upload' value='Aktualizovat'></th></tr>\n",
	"</table></form>\n";
}

sub dokumenty_clenu_storno
{
my $mainpath=get_setup('data_path','string');
$mainpath=~s#\/+$##;
my $idkraj=param('kraj')*1;
my $id=param('id')*1;
my $file=param('file')*1;
my $error='';
my $aogroup=get_setup('ao_group','number');
my ($gid,$gname,$uname,$soubor,$typ);
my $sth=$dbh->prepare("select `pf_fullname` from `phpbb_profile_fields_data`
		where `user_id`=?");
$sth->execute($id) or die $sth->errstr;
$sth->bind_columns(\($uname));
$sth->fetch;
$sth->finish;
my %prava;
if($method eq 'post')
	{
	if(param('ano'))
		{
		$dbh->do("lock tables `evidence_dokumenty` write");
		$sth=$dbh->prepare("update `evidence_dokumenty` set
					`zneplatnil`=?,
					`zneplatneno`=NOW()
				where `id`=?");
		$sth->execute("$user;$userid",$file) or die $sth->errstr;
		$sth->finish;
		$dbh->do("unlock tables");
		print "<b>Zneplatněno</b> (id=$file)";
		&dokumenty_clenu;
		return;
		}
	else
		{
		param('fce',6);
		&dokumenty_clenu;
		return;
		}
	}
else
	{
	$sth=$dbh->prepare("select `soubor`,`druh`,`smi_cist`,`smi_menit` from `evidence_dokumenty`
				where `id`=?");
	$sth->execute($file) or die $sth->errstr;
	$sth->bind_columns(\($soubor,$typ,%prava->{'1'}->{videt},%prava->{'1'}->{menit}));
	$sth->fetch;
	$sth->finish;
	}
DCS:
print	"<h2>Evidence dokumentů členů",ukaz_kraj($idkraj),"</h2>\n";
print	"<p>Storno ",($typ > 1 and $typ < 5 ? 'veřejného' : 'soukromého'),
	" dokumentu/souboru <b>$soubor</b> pro <b>$uname</b></p>\n",
	"<form action='index.cgi#a$id' method='post'>",
	"<input type='hidden' name='fce' value=$fce>",
	"<input type='hidden' name='kraj' value=$idkraj>",
	"<input type='hidden' name='id' value=$id>",
	"<input type='hidden' name='file' value=$file>",
	"<input type='hidden' name='acr_1' value='",%prava->{'1'}->{videt},"'>",
	"<input type='hidden' name='acw_1' value='",%prava->{'1'}->{menit},"'>";
if($error)
	{
	print "<h3 class='red'>$error</h3>\n";
	}
print	"<div>Chceš zneplatnit tento soubor?",
	"&nbsp;&nbsp;<input name='ne' type='submit' value='Ne'>",
	"&nbsp;&nbsp;<input name='ano' type='submit' value='Ano'>",
	"</div></form>\n";
}

sub dokumenty_clenu_novy
{
my $mainpath=get_setup('data_path','string');
$mainpath=~s#\/+$##;
my $ext1=get_setup('dokumenty_prihlaska_ext','string');
my $ext2=get_setup('dokumenty_avatar_ext','string');
my $ext3=get_setup('dokumenty_foto_ext','string');
my $ext4=get_setup('dokumenty_jine_verejne_ext','string');
my $ext5=get_setup('dokumenty_jine_neverejne_ext','string');
my $idkraj=param('kraj')*1;
my $id=param('id')*1;
my $file=lecit(param('file')) || '';
my $filetype=param('filetype')*1;
my $newname=lecit(param('filename'));
my $error='';
my $aogroup=get_setup('ao_group','number');
my $pksgroups=get_setup('pksgroups','string');
my ($gid,$gname,$uname);
my $sth=$dbh->prepare("select `pf_fullname` from `phpbb_profile_fields_data`
		where `user_id`=?");
$sth->execute($id) or die $sth->errstr;
$sth->bind_columns(\($uname));
$sth->fetch;
my %prava;
if(defined Vars->{acr_1})
	{
	%prava->{'1'}->{videt}=param('acr_1');
	}
else
	{
	%prava->{'1'}->{videt}=$pksgroups;
	%prava->{'1'}->{videt}=~s/(\d+)/G$1/g;
#	%prava->{'1'}->{videt}="U$id" . "," . %prava->{'1'}->{videt};
	}
if(defined Vars->{acw_1})
	{
	%prava->{'1'}->{menit}=param('acw_1');
	}
else
	{
	%prava->{'1'}->{menit}="G$aogroup";
	}
%prava->{'1'}->{popis}="Soubor uživatele '$uname'";
if($method eq 'post')
	{
	if(param('cur_1'))
		{
		vyber_clena("- uživatelé s přístupem pro čtení",'r',1,%prava);
		return;		}
	elsif(param('cuw_1'))
		{
		vyber_clena("- uživatelé s přístupem pro zápis",'w',1,%prava);
		return;
		}
	elsif(param('cgr_1'))
		{
		vyber_skupinu("- skupiny s přístupem pro čtení",'r',1,%prava);
		return;		}
	elsif(param('cgw_1'))
		{
		vyber_skupinu("- skupiny s přístupem pro zápis",'w',1,%prava);
		return;
		}
	elsif(param('vyber'))
		{
		my @pars=param();
		foreach my $p(@pars)
			{
			if(substr($p,0,4) eq 'usr_')
				{
				$p=~m/^\D+_(\d+)$/;
				my $u=$1;
				if(param('access') eq 'r')
					{
					%prava->{'1'}->{videt}="U$u," . %prava->{'1'}->{videt};
					}
				}
			elsif(substr($p,0,4) eq 'usw_')
				{
				$p=~m/^\D+_(\d+)$/;
				my $u=$1;
				if(param('access') eq 'w')
					{
					%prava->{'1'}->{menit}="U$u," . %prava->{'1'}->{menit};
					}
				}
			elsif(substr($p,0,4) eq 'gnr_')
				{
				$p=~m/^\D+_(\d+)$/;
				my $g=$1;
				if(param('access') eq 'r')
					{
					if(param("glr_$g"))
						{
						%prava->{'1'}->{videt}=%prava->{'1'}->{videt} . ",G$g" . 'L';
						}
					else
						{
						%prava->{'1'}->{videt}=%prava->{'1'}->{videt} . ",G$g";
						}
					}
				}
			elsif(substr($p,0,4) eq 'gnw_')
				{
				$p=~m/^\D+_(\d+)$/;
				my $g=$1;
				if(param('access') eq 'w')
					{
					if(param("glw_$g"))
						{
						%prava->{'1'}->{menit}=%prava->{'1'}->{menit} . ",G$g" . 'L';
						}
					else
						{
						%prava->{'1'}->{menit}=%prava->{'1'}->{menit} . ",G$g";
						}
					}
				}
			}
		}
	else
		{
		$file=~s/[\r\n]//sg;
		my $ext='';
		if($file=~m/^.+\.(.+)$/)
			{
			$ext=lc($1);
			}
		if(! $file)
			{
			$error="Nebyl vybrán soubor pro odeslání.";
			goto DCN;
			}
		elsif($filetype*1 < 1 or $filetype*1 > 4)
			{
			$error="Nebyl vybrán typ soubor.";
			goto DCN;
			}
		elsif($filetype==1 and ! 1*(",$ext1,")=~m/,$ext,/)
			{
			$error="Nepovolený typ souboru 'přihláška'.";
			goto DCN;
			}
		elsif($filetype==2 and ! 1*(",$ext2,")=~m/,$ext,/)
			{
			$error="Nepovolený typ souboru 'avatar'.";
			goto DCN;
			}
		elsif($filetype==3 and ! 1*(",$ext3,")=~m/,$ext,/)
			{
			$error="Nepovolený typ souboru 'foto'.";
			goto DCN;
			}
		elsif($filetype==4 and ! 1*(",$ext4,")=~m/,$ext,/)
			{
			$error="Nepovolený typ souboru 'jiný veřejný'.";
			goto DCN;
			}
		elsif($filetype==5 and ! 1*(",$ext5,")=~m/,$ext,/)
			{
			$error="Nepovolený typ souboru 'jiný soukromý'.";
			goto DCN;
			}
		my $filename=lc($file);
		$filename=~s#\\#/#g;
		$filename=~s#^.+/(.+)$#$1#;
		if($filetype > 3 and length($newname) > 0)
			{
			unless(is_ascii($newname))
				{
				$error="Nepovolené znaky v názvu souboru.";
				goto DCN;
				}
			$filename=~s/^(.+)(\..*)$/$1/;
			$filename="$newname$2";
			if($filetype > 3 and ($newname eq 'prihlaska' or $newname eq 'foto' or $newname eq 'avatar'))
				{
				$error="Toto je vyhrazený název souboru.";
				goto DCN;
				}
			}
		elsif($filetype > 3 and ! is_ascii($filename))
			{
			$error="Nepovolené znaky v názvu souboru.";
			($newname=$filename)=~s/^(.+)\..*$/$1/;
			goto DCN;
			}
		my $path;
		if($filetype > 1 and $filetype < 5)
			{
			$path="$mainpath/public";
			unless(-d $path)
				{
				mkdir $path or $error="Nelze vytvořit adresář '$path'";
				goto DCN if($error);
				}
			$path="$mainpath/public/$id/";
			}
		else
			{
			$path="$mainpath/$id/";
			}
		unless(-d $path)
			{
			mkdir $path or $error="Nelze vytvořit adresář uživatele '$path'";
			}
		goto DCN if($error);
		if($filetype==1)
			{
			$filename="prihlaska.$ext";
			if(-e "$path$filename")
				{
				$error="Přihláška člena již existuje, použij funkci 'Změnit'";
				goto DCN;
				}
			}
		elsif($filetype==2)
			{
			$filename="avatar.$ext";
			if(-e "$path$filename")
				{
				$error="Avatar již existuje, použij funkci 'Změnit'";
				goto DCN;
				}
			}
		elsif($filetype==3)
			{
			$filename="foto.$ext";
			if(-e "$path$filename")
				{
				$error="Foto již existuje, použij funkci 'Změnit'";
				goto DCN;
				}
			}
		else
			{
			if(-e "$path$filename")
				{
				$error="Soubor již existuje, použij funkci 'Změnit'";
				goto DCN;
				}
			}
		open O,"> $path$filename" or $error="Nelze vytvořit soubor '$path$filename'";
		goto DCN if($error);
		binmode O;
		while(<$file>)
			{
			print O $_ or $error="Chyba při zápisu do souboru '$path$filename'";
			}
		close O;
		goto DCN if($error);
		$dbh->do("lock tables `evidence_dokumenty` write");
		my $sth=$dbh->prepare("insert into `evidence_dokumenty` set
					`user_id`=?,
					`soubor`=?,
					`vlozeno`=now(),
					`vlozil`=?,
					`smi_cist`=?,
					`smi_menit`=?,
					`druh`=?");
		%prava->{'1'}->{videt}=~s/,+/,/sg;
		%prava->{'1'}->{videt}=~s/^,|,$//sg;
		%prava->{'1'}->{videt}=~s/(\d|L)(U|G)/$1,$2/sg;
		%prava->{'1'}->{menit}=~s/^,|,$//sg;
		%prava->{'1'}->{menit}=~s/,+/,/sg;
		%prava->{'1'}->{menit}=~s/(\d|L)(U|G)/$1,$2/sg;
		$sth->execute($id,$filename,"$user;$userid",%prava->{'1'}->{videt},%prava->{'1'}->{menit},$filetype) or $error="Chyba databáze: " . $sth->errstr;
		if($error)
			{
			$sth->finish;
			$dbh->do("unlock tables");
			goto DCN ;
			}
		$sth=$dbh->prepare("select last_insert_id()");
		$sth->execute() or $error="Nelze uložit do databáze. ERROR: " . $sth->errstr;
		my ($fid)=$sth->fetchrow_array();
		$sth->finish;
		$dbh->do("unlock tables");
		print "<b>Uloženo</b> (id=$fid)";
		param('fce',6);
		&dokumenty_clenu;
		return;
		}
	}
DCN:
print	"<h2>Evidence dokumentů členů",ukaz_kraj($idkraj),"</h2>\n";
#print "<p>Access: $access[0] $access[1]</p>";
#print "<p>GrpAccess: $grpaccess[0] $grpaccess[1] $grpaccess[2] $grpaccess[3]</p>";
#print "<p>User: $userid</p>";
print	"<p>Nový dokument pro <b>$uname</b></p>\n",
	"<form action='index.cgi#a$id' method='post' enctype='multipart/form-data'>",
	"<input type='hidden' name='fce' value=$fce>",
	"<input type='hidden' name='kraj' value=$idkraj>",
	"<input type='hidden' name='id' value=$id>",
	"<input type='hidden' name='acr_1' value='",%prava->{'1'}->{videt},"'>",
	"<input type='hidden' name='acw_1' value='",%prava->{'1'}->{menit},"'>",
	"<table>\n";
if($error)
	{
	print "<caption>$error</caption>\n";
	}
my ($dis1,$dis2,$dis3)=(0)x3;
$sth=$dbh->prepare("select count(*) from `evidence_dokumenty`
		where `soubor` like ? and user_id=?");
foreach my $ext(split(/,/,$ext1))
	{
	$dis1=1 if(-e "$mainpath/$id/prihlaska.$ext");
	$sth->execute("prihlaska.$ext",$id) or die $sth->errstr;
	my ($c)=$sth->fetchrow_array();
	$dis1=1 if($c);
	}
foreach my $ext(split(/,/,$ext2))
	{
	$dis2=1 if(-e "$mainpath/public/$id/avatar.$ext");
	$sth->execute("avatar.$ext",$id) or die $sth->errstr;
	my ($c)=$sth->fetchrow_array();
	$dis2=1 if($c);
	}
foreach my $ext(split(/,/,$ext3))
	{
	$dis3=1 if(-e "$mainpath/public/$id/foto.$ext");
	$sth->execute("foto.$ext",$id) or die $sth->errstr;
	my ($c)=$sth->fetchrow_array();
	$dis3=1 if($c);
	}
$sth->finish;
print	"<tr><td>Soubor</td><td><input name='file' type='file'></td></tr>\n",
	"<tr><td>Typ souboru</td><td>";
if($access[1] or $grpaccess[2])
	{
	print "<input name='filetype' type='radio' value='1' onclick=\"dinput('filename')\"",
		($dis1 ? " disabled title='Soubor existuje nebo má existovat, použij funkci Změnit'" : ''),
		($filetype==1 and !$dis1 ? ' checked' : ''),
		"><b>přihláška</b> <i>(povoleno: $ext1)</i><br>";
	}
if($access[1] or $grpaccess[2])
	{
	print "<input name='filetype' type='radio' value='2' onclick=\"dinput('filename')\"",
		($dis2 ? " disabled title='Soubor existuje nebo má existovat, použij funkci Změnit'" : ''),
		($filetype==2 ? ' checked' : ''),
		"><b>avatar</b> <i>(povoleno: $ext2)</i><br>";
	}
if($access[1] or $grpaccess[2] or $id==$userid)
	{
	print "<input name='filetype' type='radio' value='3' onclick=\"dinput('filename')\"",
		($dis3 ? " disabled title='Soubor existuje nebo má existovat, použij funkci Změnit'" : ''),
		($filetype==3 ? ' checked' : ''),
		"><b>foto</b> <i>(povoleno: $ext3)</i><br>";
	}
if($access[1] or $grpaccess[2] or $id==$userid)
	{
	print "<input name='filetype' type='radio' value='4' onclick=\"einput('filename')\"",
		($filetype==4 ? ' checked' : ''),
		"><b>jiný&nbsp;veřejný</b> <i>(povoleno: $ext4)</i><br>";
	}
if($access[1] or $grpaccess[2] or $id==$userid)
	{
	print "<input name='filetype' type='radio' value='5' onclick=\"einput('filename')\"",
		($filetype==5 ? ' checked' : ''),
		"><b>jiný&nbsp;soukromý</b> <i>(povoleno: $ext5)</i>",
	"<br>Jméno souboru:&nbsp;<input id='filename' name='filename' type='text' value='$newname' maxlenght=255",
		($filetype > 3 ? '' : ' disabled'),
		"> <i>(bez diakritiky, mezer a přípony)</i>";
	}
print	"</td></tr>\n",
	"<tr><td>Smí vidět</td><td><div style='height: 12em; overflow-y: scroll; overflow-x: show; white-space: nowrap; margin: 0.2em 0 0.2em 0; width: 20em;'>";
	showusers('U',%prava->{'1'}->{videt});
	showusers('G',%prava->{'1'}->{videt});
print	"</div>";
if($access[1] or $grpaccess[2])
	{
	print	"<input type='submit' name='cur_1' value='Členové'>",
		"&nbsp;&nbsp;<input type='submit' name='cgr_1' value='Skupiny'>";
	}
print	"</td></tr>",
	"<tr><td>Smí měnit</td><td><div style='height: 12em; overflow-y: scroll; overflow-x: show; white-space: nowrap; margin: 0.2em 0 0.2em 0; width: 20em;'>";
	showusers('U',%prava->{'1'}->{menit});
	showusers('G',%prava->{'1'}->{menit});
print	"</div>";
if($access[1] or $grpaccess[2])
	{
	print	"<input type='submit' name='cuw_1' value='Členové'>",
		"&nbsp;&nbsp;<input type='submit' name='cgw_1' value='Skupiny'>";
	}
print	"</td></tr>",
	"<tr><th colspan=2><input class='bold' type='submit' name='upload' value='Vložit'></th></tr>\n",
	"</table></form>\n";
}

sub dokumenty_clenu_evid
{
my $mainpath=get_setup('data_path','string');
$mainpath=~s#\/+$##;
my $idkraj=param('kraj')*1;
my $id=param('id')*1;
my $file=param('file');
my $error='';
my ($gid,$gname,$uname);
my $sth=$dbh->prepare("select `pf_fullname` from `phpbb_profile_fields_data`
		where `user_id`=?");
$sth->execute($id) or die $sth->errstr;
$sth->bind_columns(\($uname));
$sth->fetch;
print	"<h2>Evidence dokumentů členů",ukaz_kraj($idkraj),"</h2>\n",
	"<p>Zaevidování dokumentu \"<b>$file</b>\" pro <b>$uname</b></p>\n",
	"<form action='index.cgi#a$id' method='post'>",
	"<input type='hidden' name='fce' value=$fce>",
	"<input type='hidden' name='kraj' value=$idkraj>",
	"<input type='hidden' name='id' value=$id>",
	"<input type='hidden' name='file' value='$file'>",
	"<table>\n";
if($error)
	{
	print "<caption>$error</caption>\n";
	}
$sth=$dbh->prepare("select `group_id`,`group_name` from `phpbb_groups` order by `group_name`");
print	"<tr><td>Oprávnění ke čtení</td><td class='white-space: nowrap;'>",
	"<div class='vscroll' style='height: 10em; width: 30em;'>";
$sth->execute() or die $sth->errstr;
$sth->bind_columns(\($gid,$gname));
while ($sth->fetch)
	{
	print	"<input type='checkbox' name='r_$gid' id='r_$gid' ",
		"onclick=\"refrchk('r_$gid','rv_$gid')\"",
		(param('r_' . $gid) ? ' checked' : ''),
		">$gname&nbsp;&nbsp;",
		"<input type='checkbox' name='rv_$gid' id='rv_$gid'",
		(param('rv_' . $gid) ? ' checked' : ''),
		(param('r_' . $gid) ? '' : ' disabled'),
		">jen vedoucí<br>";
		
	}
print	"</div></td></tr>\n",
	"<tr><td>Oprávnění k zápisu</td><td class='white-space: nowrap;'>",
	"<div class='vscroll' style='height: 10em; width: 20em;'>";
$sth->execute() or die $sth->errstr;
$sth->bind_columns(\($gid,$gname));
while ($sth->fetch)
	{
	print	"<input type='checkbox' name='w_$gid'",
		(param('w_' . $gid) ? ' checked' : ''),
		">$gname&nbsp;&nbsp;<br>";
	}
print "</div></td></tr>\n",
	"<tr><td>Oprávnění ke zneplatnění</td><td class='white-space: nowrap;'>",
	"<div class='vscroll' style='height: 10em; width: 20em;'>";
$sth->execute() or die $sth->errstr;
$sth->bind_columns(\($gid,$gname));
while ($sth->fetch)
	{
	print	"<input type='checkbox' name='x_$gid'",
		(param('x_' . $gid) ? ' checked' : ''),
		">$gname&nbsp;&nbsp;<br>";
	}
print	"</div></td></tr>\n",
	"<tr><th colspan=2><input type='submit' name='ok' value='OK'></th></tr>\n",
	"</table></form>\n";
$sth->finish;
}

sub dokumenty_clenu
{
my $mainpath=get_setup('data_path','string');
$mainpath=~s#\/+$##;
my $idkraj=param('kraj')*1;
my $set=($idkraj==-1 ? get_setup('ksgroups','string') : $idkraj);
print	"<h2>Evidence dokumentů členů",ukaz_kraj($idkraj),"</h2>\n";
#print "<p>Access: $access[0] $access[1]</p>";
#print "<p>GrpAccess: $grpaccess[0] $grpaccess[1] $grpaccess[2] $grpaccess[3]</p>";
#print "<p>User: $userid</p>";
if($method eq 'post')
	{
	my ($id,$name,$fullname,$type,$group,$clenid);
	my ($fid,$soubor,$vlozil,$vlozeno,$aktualizoval,$aktualizace,$zneplatnil,$zneplatneno,$druh);
	$dbh->do("lock tables `phpbb_profile_fields_data` read,
			`phpbb_user_group` read,
			`phpbb_users` read,
			`phpbb_groups` read,
			`evidence_setup` read,
			`evidence_dokumenty` write");
	my $sth=$dbh->prepare("SELECT `phpbb_user_group`.`user_id`,`username`,
				`pf_fullname`,`user_type`,`group_name`,
				`pf_idclena`
			FROM `phpbb_user_group`
			LEFT JOIN `phpbb_users`
				ON(`phpbb_users`.`user_id`=`phpbb_user_group`.`user_id`)
			LEFT JOIN `phpbb_groups`
				ON(`phpbb_groups`.`group_id`=`phpbb_user_group`.`group_id`) 
			LEFT JOIN `phpbb_profile_fields_data`
				ON(`phpbb_profile_fields_data`.`user_id`=`phpbb_users`.`user_id`)
#				WHERE `phpbb_user_group`.`group_id`=$idkraj
			WHERE FIND_IN_SET(`phpbb_user_group`.`group_id`,'$set')
			ORDER BY 5,2");
	my $sth1=$dbh->prepare("select `id`,
				`vlozil`,date_format(`vlozeno`,'%d.%m.%Y'),
				`aktualizoval`,date_format(`aktualizace`,'%d.%m.%Y'),
				`zneplatnil`,date_format(`zneplatneno`,'%d.%m.%Y')
			from `evidence_dokumenty`
			where `user_id`=? and `soubor` like ?
			order by `soubor`");
	my $sth2=$dbh->prepare("select `id`,`soubor`,
				`vlozil`,date_format(`vlozeno`,'%d.%m.%Y'),
				`aktualizoval`,date_format(`aktualizace`,'%d.%m.%Y'),
				`zneplatnil`,date_format(`zneplatneno`,'%d.%m.%Y'),
				`druh`
			from `evidence_dokumenty`
			where `user_id`=?
			order by `soubor`");
	$sth->execute() or do_die($sth->errstr);
	$sth->bind_columns(\($id,$name,$fullname,$type,$group,$clenid));
	print	"<table><caption class='norm'>",$sth->rows," členů</caption>\n",
		"<tr class='hdr'>",
		"<td>Číslo</td><td>Člen</td><td>Plné jméno</td>",
		($set=~m/,/ ? "<td>Kraj</td>" : ''),
		"<td>Dokumenty</td>\n",
		"</tr>\n";
	while ($sth->fetch)
		{
		my %files;
		$fullname.=' ' unless($fullname);
		my $u16;
		if($iswin)
			{
			$u16 = $mapw->to_unicode($fullname);
			}
		if($type==1 or $type==2)
			{
			my $t=($type==1 ? 'inactive' : 'bot');
			print	"<tr class='bgred'><td class='ri' title='path=/$idkraj/$id/'>",
				"<a name='a",$id*1,"' class='name'>$clenid</a></td><td>$name</td>",
				"<td>",($iswin ? $mapw->to8($u16) : $fullname),
				" ($t)</td>";
			}
		else
			{
			print	"<tr><td class='ri' title='path=/$id/'>",
				"<a name='a",$id*1,"' class='name'>$clenid</a></td><td>$name</td>",
				"<td>",($iswin ? $mapw->to8($u16) : $fullname),"</td>";
			}
		print	'',($set=~m/,/ ? "<td>$group</td>" : ''),
			"<td><table class='nobord'>";
		my $nofile=1;
		if(-d "$mainpath/$id")
			{
			my $ok=1;
			opendir (DIR,"$mainpath/$id") or $ok=0;
			if($ok)
				{
				my @files = grep { /^[^\.]/ && -e "$mainpath/$id/$_" } readdir(DIR);
				closedir DIR;
				foreach my $file(reverse sort @files)
					{
					$sth1->execute($id,$file) or die $sth1->errstr;
					$sth1->bind_columns(\($fid,$vlozil,$vlozeno,$aktualizoval,$aktualizace,$zneplatnil,$zneplatneno));
					if($sth1->rows)
						{
						$sth1->fetch;
						%files->{$fid}=$file;
						$nofile=0;
						$vlozil=~s/^(.+);.+$/$1/;
						$aktualizoval=~s/^(.+);.+$/$1/;
						$zneplatnil=~s/^(.+);.+$/$1/;
						my $class=($zneplatneno=~m/^00\./ ? 'bold' : 'bold strike');
						print	"<tr><td><a name='found$fid' class='$class' title=\"",
							"Vložil: $vlozil $vlozeno";
						print	"\nAktualizoval: $aktualizoval $aktualizace" unless($aktualizace=~m/^00\./);
						print	"\nZneplatnil: $zneplatnil $zneplatneno" unless($zneplatneno=~m/^00\./);
						print	"\">$file</a></td>",
							"<td><a class='viewbut' href='../filesend.cgi?file=$fid&req=$userid' target='_blank' title='Zobrazit nebo stáhnout soubor'>Ukázat</a></td><td>";
						print "<a class='editbut' href='index.cgi?file=$fid&kraj=$idkraj&id=$id&fce=62' title='Změnit oprávnění, nebo uploadovat nový soubor'>Změnit</a>" if($aktualizace=~m/^00\./ and checkdocaccess($fid));
						print "<td>";
						print "<a class='delbut' href='index.cgi?file=$fid&kraj=$idkraj&id=$id&fce=63' title='Zneplatnit soubor'>Storno</a>" if($zneplatneno=~m/^00\./ and checkdocaccess($fid));
						print "</td></tr>\n";
						}
					else
						{
						print "<tr><td colspan=4><span class='bold red'>$file</span>&nbsp;";
						if(checkdocaccess($fid))
							{
							print	"<form class='inter' action='index.cgi#a",$id*1,"' method='post'>",
								"<input type='hidden' name='kraj' value='$idkraj'>",
								"<input type='hidden' name='fce' value=60>",
								"<input type='hidden' name='id' value='$id'>",
								"<input type='hidden' name='file' value='$file'>",
								"<input type='submit' name='regbut' value='Zaevidovat' title='Zaevidovat soubor do databáze'></form>";
							}
						print "</td></tr>\n";
						$nofile=0;
						}
					$sth1->finish;
					}
#					print "<a class='addbut' href='index.cgi?kraj=$idkraj&id=$id&fce=61'>Nový soubor</a>";
				}
			else
				{
				closedir DIR;
				}
			}
		if(-d "$mainpath/public/$id")
			{
			my $ok=1;
			opendir (DIR,"$mainpath/public/$id") or $ok=0;
			if($ok)
				{
				my @files = grep { /^[^\.]/ && -e "$mainpath/public/$id/$_" } readdir(DIR);
				closedir DIR;
				foreach my $file(reverse sort @files)
					{
					$sth1->execute($id,$file) or die $sth1->errstr;
					$sth1->bind_columns(\($fid,$vlozil,$vlozeno,$aktualizoval,$aktualizace,$zneplatnil,$zneplatneno));
					if($sth1->rows)
						{
						$sth1->fetch;
						%files->{$fid}=$file;
						$nofile=0;
						$vlozil=~s/^(.+);.+$/$1/;
						$aktualizoval=~s/^(.+);.+$/$1/;
						$zneplatnil=~s/^(.+);.+$/$1/;
						my $class=($zneplatneno=~m/^00\./ ? 'norm' : 'strike');
						print	"<tr><td><a name='found$fid' class='$class' title=\"",
							"Vložil: $vlozil $vlozeno";
						print	"\nAktualizoval: $aktualizoval $aktualizace" unless($aktualizace=~m/^00\./);
						print	"\nZneplatnil: $zneplatnil $zneplatneno" unless($zneplatneno=~m/^00\./);
						print	"\">$file</a></td>",
							"<td><a class='viewbut' href='../filesend.cgi?file=$fid&req=$userid' target='_blank' title='Zobrazit nebo stáhnout soubor'>Ukázat</a></td><td>";
						print "<a class='editbut' href='index.cgi?file=$fid&kraj=$idkraj&id=$id&fce=62' title='Změnit oprávnění, nebo uploadovat nový soubor'>Změnit</a>" if($aktualizace=~m/^00\./ and checkdocaccess($fid));
						print "<td>";
						print "<a class='delbut' href='index.cgi?file=$fid&kraj=$idkraj&id=$id&fce=63' title='Zneplatnit soubor'>Storno</a>" if($zneplatneno=~m/^00\./ and checkdocaccess($fid));
						print "</td></tr>\n";
						}
					else
						{
						print "<tr><td colspan=4><span class='red'>$file</span>&nbsp;";
						if(checkdocaccess($fid))
							{
							print	"<form class='inter' action='index.cgi#a",$id*1,"' method='post'>",
								"<input type='hidden' name='kraj' value='$idkraj'>",
								"<input type='hidden' name='fce' value=60>",
								"<input type='hidden' name='id' value='$id'>",
								"<input type='hidden' name='file' value='$file'>",
								"<input type='submit' name='regbut' value='Zaevidovat' title='Zaevidovat soubor do databáze'></form>";
							}
						print "</td></tr>\n";
						$nofile=0;
						}
					$sth1->finish;
					}
#					print "<a class='addbut' href='index.cgi?kraj=$idkraj&id=$id&fce=61'>Nový soubor</a>";
				}
			else
				{
				closedir DIR;
				}
			}
		if($nofile)
			{
			print "<tr><td colspan=4><i>žádné soubory</i></td></tr>\n";
			}
		$sth2->execute($id) or die $sth2->errstr;
		if($sth2->rows)
			{
			$sth2->bind_columns(\($fid,$soubor,$vlozil,$vlozeno,$aktualizoval,$aktualizace,$zneplatnil,$zneplatneno,$druh));
			while ($sth2->fetch)
				{
				unless(defined %files->{$fid})
					{
					$vlozil=~s/^(.+);.+$/$1/;
					$aktualizoval=~s/^(.+);.+$/$1/;
					$zneplatnil=~s/^(.+);.+$/$1/;
					print	"<tr><td colspan=2><a name='found$fid' class='red",
						($druh > 1 and $druh < 5 ? '' : 'bold'),"' title=\"",
						"Vložil: $vlozil $vlozeno";
					print	"\nAktualizoval: $aktualizoval $aktualizace" unless($aktualizace=~m/^00\./);
					print	"\nZneplatnil: $zneplatnil $zneplatneno" unless($zneplatneno=~m/^00\./);
					print	"\">$soubor</a> - soubor nenalezen</td><td>";
					print "<a class='editbut' href='index.cgi?file=$fid&kraj=$idkraj&id=$id&fce=62' title='Změnit oprávnění, nebo uploadovat nový soubor'>Změnit</a>" if($aktualizace=~m/^00\./ and checkdocaccess($fid));
					print "</td><td>";
					print "<a class='delbut' href='index.cgi?file=$fid&kraj=$idkraj&id=$id&fce=63' title='Zneplatnit soubor'>Storno</a>" if($zneplatneno=~m/^00\./ and checkdocaccess($fid));
					print "</td></tr>\n";
					}
				}
			}
		$sth2->finish;
		print	"</table>";
		if($access[1] or $grpaccess[2] or $id==$userid)
			{
			print "<a class='addbut' href='index.cgi?kraj=$idkraj&id=$id&fce=61' title='Uploadovat nový soubor'>Nový soubor</a>";
			}
		print "</td></tr>\n";
		}
	$sth->finish;
	$dbh->do("unlock tables");
	print "</table><p>&nbsp;</p>\n";
	}
else
	{
	print "<form action='index.cgi' method='post'>\n",
		"<input type='hidden' name='fce' value='6'>\n<p>";
#	&kraje;
	if($access[0] or $access[1] or $hipriv)
		{
		&kraje(0);
		}
	elsif($grpaccess[0] or $grpaccess[2])
		{
		&kraje((krajclena())[1]);
		}
	print	"&nbsp;&nbsp;<input type='submit' value='Zobrazit'></p>\n</form>\n";
	}
}

sub cisluj_cleny
{
my ($found,$max,$idclena,$fullname,$userid,$regdate,$name);
print	"<h2>Přidělení členských čísel</h2>\n";
my $forumgroup=get_setup('maingroup','number');
my $sth=$dbh->prepare("select max(`pf_idclena`) from `phpbb_profile_fields_data`");
$sth->execute() or die $sth->errstr;
$found=$sth->fetchrow_array();
$max=get_setup('clenske_cislo','number');
if($max*1 <= $found*1)
	{
	print	"<p><b>CHYBA!</b><br>Nejvyšší existující členské číslo (<b>$found</b>) je vyšší, než ",
		"je v nastavení aplikace (<b>$max</b>).<br>Zkontroluj to a oprav položku '<b>clenske_cislo</b>' v 'Nastavení aplikace'.",
		"<br>Nezapomeň na bývalé členy, kteří měli přidělená čísla.</p>";
	$sth->finish;
	return;
	}
$dbh->do("lock tables `phpbb_user_group` read,
		`phpbb_users` read,
		`phpbb_profile_fields_data` write,
		`evidence_setup` write");
$sth=$dbh->prepare("select `pf_idclena`,`pf_fullname`,`phpbb_user_group`.`user_id`,
			`user_regdate`,`username`
		from `phpbb_user_group`
		left join `phpbb_profile_fields_data`
			on(`phpbb_user_group`.`user_id`=`phpbb_profile_fields_data`.`user_id`)
		left join `phpbb_users`
			on(`phpbb_users`.`user_id`=`phpbb_user_group`.`user_id`)
		where `phpbb_user_group`.`group_id`=? and (ISNULL(`pf_idclena`)
			or `pf_idclena`=0)
		order by `user_regdate`");
my $sth1=$dbh->prepare("update `phpbb_profile_fields_data` set
			`pf_idclena`=? where `user_id`=?");
$sth->execute($forumgroup) or die $sth->errstr;
unless($sth->rows)
	{
	$sth->finish;
	$dbh->do("unlock tables");
	print "<p><br>&nbsp;<br>Žádnému novému členu nebylo přiděleno členské číslo.</p>";
	return;
	}
$sth->bind_columns(\($idclena,$fullname,$userid,$regdate,$name));
my $cnt=0;
print	"<table>\n",
	"<tr class='hdr'>",
	"<td>Člen</td>",
	"<td>Plné jméno</td>",
	"<td>Číslo</td>",
	"</tr>\n";
while ($sth->fetch)
	{
	$fullname.=' ' unless($fullname);
	print	"<tr>",
		"<td>$name</td>",
		"<td>$fullname</td>",
		"<td>$max</td>",
		"</tr>\n";
	$sth1->execute($max,$userid) or die $sth1->errstr;
	$sth1->finish;
	$max++;
	$cnt++;
	}
print "</table>\n<p>Přiděleno $cnt členských čísel.<br>&nbsp;</p>";
$sth=$dbh->prepare("update `evidence_setup` set `number`=? where `name`=?");
$sth->execute($max,'clenske_cislo') or die $sth->errstr;
$sth->finish;
$dbh->do("unlock tables");
}

sub setup
{
my ($name,$number,$string,$text,$editable,$comment);
print	"<h2>Nastavení aplikace</h2>\n";
if($method eq 'post')
	{
	if(param('ok'))
		{
		my $sth=$dbh->prepare("select `editable` from `evidence_setup`
				where `name`=?");
		my $sth1=$dbh->prepare("update `evidence_setup` set
				`number`=?,`comment`=? where `name`=?");
		my $sth2=$dbh->prepare("update `evidence_setup` set
				`string`=?,`comment`=? where `name`=?");
		my $sth3=$dbh->prepare("update `evidence_setup` set
				`text`=?,`comment`=? where `name`=?");
		my @pars=param();
		$dbh->do("lock tables `evidence_setup` write");
		foreach my $p(@pars)
			{
			next if(substr($p,0,4) ne 'val_');
			my $var=substr($p,4);
			my $val=param($p);
			my $comment=param("com_$var");
			$sth->execute($var) or die $sth->errstr;
			$editable=$sth->fetchrow_array();
			$sth->finish;
			if($editable eq 'number')
				{
				$val*=1;
				if($var eq 'logout')
					{
					$val=int($val);
					$val=1 if($val < 1);
					}
				$sth1->execute($val,$comment,$var) or die $sth1->errstr;
				$sth1->finish;
				}
			elsif($editable eq 'string')
				{
				$sth2->execute($val,$comment,$var) or die $sth2->errstr;
				$sth2->finish;
				}
			elsif($editable eq 'strset')
				{
				$val=~s/\s//sg;
				$val=~s/,+/,/sg;
				$val=~s/^,+|,+$//sg;
				$val=~s/(\d|L)(U|G)/$1,$2/sg;
				$sth2->execute($val,$comment,$var) or die $sth2->errstr;
				$sth2->finish;
				}
			elsif($editable eq 'txtset')
				{
				$val=~s/\s//sg;
				$val=~s/,+/,/sg;
				$val=~s/^,+|,+$//sg;
				$val=~s/(\d|L)(U|G)/$1,$2/sg;
				$sth3->execute($val,$comment,$var) or die $sth3->errstr;
				$sth3->finish;
				}
			else
				{
				$sth3->execute($val,$comment,$var) or die $sth3->errstr;
				$sth3->finish;
				}
			}
		}
	print "<p><br>&nbsp;<br><b>Uloženo</b></p>";
	$dbh->do("unlock tables");
	return;
	}
my $sth=$dbh->prepare("select `name`,`number`,`string`,`text`,`editable`,`comment`
		from `evidence_setup`
		order by `name`");
$sth->execute() or die $sth->errstr;
$sth->bind_columns(\($name,$number,$string,$text,$editable,$comment));
print	"<form action='index.cgi' method='post'>",
	"<input type='hidden' name='fce' value='$fce'>\n",
	"<table>\n",
	"<tr class='hdr'>",
	"<td>Pole</td>",
	"<td>Hodnota</td>",
	"<td>Komentář</td>",
	"</tr>\n";
if($iswin) {use utf8;}
while ($sth->fetch)
	{
	print	"<tr><td class='top'><b>$name</b></td><td class='top'>";
	if($editable eq 'number')
		{
		print "<input type='text' name='val_$name' value='",$number*1,"' maxlength=18>";
		}
	elsif($editable eq 'string' or $editable eq 'strset')
		{
		print "<input class='string' type='text' name='val_$name' value='$string' maxlength=255>";
		}
	else
		{
		print "<textarea name='val_$name' cols=50 rows=10>$text</textarea>";
		}
	print	"</td>",
		"<td class='top'><textarea name='com_$name' cols=25 rows=5>$comment</textarea></td>",
		"</tr>\n";
	}
$sth->finish;
print	"<tr><th colspan=3><input name='ok' type='submit' value='Uložit změny'></th></tr>\n",
	"</table>\n</form>";
}

sub getgroups
{
my $mask=shift;
my ($gid,$set);
$set='';
my $sth=$dbh->prepare("SELECT `group_id` from `phpbb_groups`
			WHERE LEFT(`group_name`,3)='$mask'");
$sth->execute() or die $sth->errstr;
$sth->bind_columns(\($gid));
while ($sth->fetch)
	{
	$set.="$gid,";
	}
$set=substr($set,0,-1);
$sth->finish;
return $set;
}

sub dluznici
{
my ($set,$id,$name,$fullname,$datprisp,$castka,$datupom,$clenstvi,$kraj,$dnes,$clenid,$dalsi);
my ($sec,$min,$hour,$mday,$mon,$year,$wday,$yday,$isdst) = localtime(time);
$mon++;
$year = 1900 + $year;
$dnes=1 * sprintf("%04d%02d%02d",$year,$mon,$mday);
my $filtr='';
if($access[0] or $access[1] or $hipriv)
	{
	$set=get_setup('ksgroups','string');
	}
elsif($grpaccess[0] or $grpaccess[2])
	{
	($filtr,$set)=krajclena();
	$filtr=' - ' . $filtr;
	}
my $suma=0;
my $sth=$dbh->prepare("SELECT `phpbb_users`.`user_id`,`username`,
			`pf_fullname`,`pf_datumclprispevku`,
			`pf_vyseclprispevku`,`pf_datumupominky`,
			`pf_vznikclenstvi`,`group_name`,`pf_idclena`,
			`pf_dalsiclprispevek`
		FROM `phpbb_user_group`
		LEFT JOIN `phpbb_users`
			ON(`phpbb_users`.`user_id`=`phpbb_user_group`.`user_id`)
		LEFT JOIN `phpbb_groups`
			ON(`phpbb_groups`.`group_id`=`phpbb_user_group`.`group_id`)
		LEFT JOIN `phpbb_profile_fields_data`
			ON(`phpbb_profile_fields_data`.`user_id`=`phpbb_users`.`user_id`)
		WHERE FIND_IN_SET(`phpbb_user_group`.`group_id`,'$set')
		ORDER BY 8,2");
$sth->execute() or die $sth->errstr;
$sth->bind_columns(\($id,$name,$fullname,$datprisp,$castka,$datupom,$clenstvi,$kraj,$clenid,$dalsi));
print	"<h2>Dlužníci$filtr</h2><table>\n",
	"<tr class='hdr'>",
	"<td>Číslo</td>",
	"<td>Člen</td>",
	"<td>Plné jméno</td>",
	"<td>Členem od</td>",
	"<td>Placeno</td>",
	"<td>Částka</td>",
	"<td>Upomínka</td>",
	"<td>Další&nbsp;platba</td>",
	"<td>Kraj</td>",
	"</tr>\n";
my $cnt=0;
while ($sth->fetch)
	{
	$datprisp=~s/\s//g;
	$datupom=~s/\s//g;
	$clenstvi=~s/\s//g;
	$dalsi=~s/\s//g;
	my ($den,$mes,$rok)=split(/\-/,$datprisp);
	my $dp=sprintf("%02d.%02d.%04d",$den,$mes,$rok);
	$dp='&nbsp;' if($dp eq '00.00.0000');
	my $ndp=sprintf("%04d%02d%02d",$rok,$mes,$den);
	($den,$mes,$rok)=split(/\-/,$datupom);
	my $du=sprintf("%02d.%02d.%04d",$den,$mes,$rok);
	my $ndu=sprintf("%04d%02d%02d",$rok,$mes,$den);
	($den,$mes,$rok)=split(/\-/,$clenstvi);
	my $dc=sprintf("%02d.%02d.%04d",$den,$mes,$rok);
	my $ndc=sprintf("%04d%02d%02d",$year,$mes,$den);
	($den,$mes,$rok)=split(/\-/,$dalsi);
	my $ddp=sprintf("%02d.%02d.%04d",$den,$mes,$rok);
	$ddp='&nbsp;' if($ddp eq '00.00.0000');
	my $nddp=sprintf("%04d%02d%02d",$rok,$mes,$den);
	next if($dnes <= $ndp + 10000 or ($ndc > $dnes and $nddp > $dnes));
	$cnt++;
	$suma+=$castka;
	$castka='&nbsp;' if($castka==0);
	$fullname.=' ' unless($fullname);
	print	"<tr><td class='ri'>$clenid</td><td>$name</td>",
		"<td>$fullname</td>",
		"<td>$dc</td><td>$dp</td><td class='nwr'>$castka</td>",
		"<td>$du</td><td>$ddp</td><td>$kraj</td></tr>\n";
	}
print "<tr><th class='cent' colspan=9>Celkem ",$cnt*1," dlužníků, dlužná částka: ",
	$suma*1," Kč</th></tr></table><p>&nbsp;</p>\n";
$sth->finish;
}

sub vznik_clenstvi
{
my $idkraj=param('kraj')*1;
my $set=($idkraj==-1 ? get_setup('ksgroups','string') : $idkraj);
print	"<h2>Vznik členství členů ",ukaz_kraj($idkraj),"</h2>",
	"<form action='index.cgi' method='post'>\n",
	"<input type='hidden' name='fce' value='2'>\n";
if($method eq 'post')
	{
	if(param('ok'))
		{
		my $cnt=my $err=0;
		my @pars=param();
		my $sth=$dbh->prepare("update `phpbb_profile_fields_data` set
					`pf_vznikclenstvi`=?
				where `user_id`=?");
		my $sth1=$dbh->prepare("select date(?)");
		my $sth2=$dbh->prepare("select `pf_vznikclenstvi`
					from `phpbb_profile_fields_data`
					where `user_id`=?");
		my $sth3=$dbh->prepare("insert into `phpbb_profile_fields_data` set
					`pf_vznikclenstvi`=?,`user_id`=?");
		$dbh->do("lock tables `phpbb_profile_fields_data` write");
		my ($err1, $err2)=(0,0);
		foreach my $p(@pars)
			{
			next if(substr($p,0,2) ne 'd_');
			my $id=substr($p,2)*1;
			my $dat=param($p);
			$dat=~s/\s//g;
			if($dat=~m/^(\d{1,2}).(\d{1,2}).(\d{1,4})$/)
				{
				my ($den,$mes,$rok)=($1,$2,$3);
				$rok+=2000 if($rok < 100 and $rok > 0);
				$dat=sprintf("%2d-%2d-%4d",$den,$mes,$rok);
				unless($rok==0 and $mes==0 and $den==0)
					{
					$sth1->execute("$rok-$mes-$den") or do_die($sth1->errstr);
					my ($d)=$sth1->fetchrow_array;
					$sth1->finish;
					unless($d*1)
						{
						$err++;
						$sth2->execute($id) or do_die($sth2->errstr);
						($dat)=$sth2->fetchrow_array;
						$sth2->finish;
						}
					}
				}
			else
				{
				$dat='00-00-0000';
				}
			my $ok=1;
			if(find_id($id))
				{
				$sth->execute($dat,$id) or $ok=0;
				$sth->finish;
				$err1++ unless($ok)
				}
			else
				{
				$sth3->execute($dat,$id) or $ok=0;
				$sth3->finish;
				$err2++ unless($ok);
				}
			$cnt++ if($ok);
			}
		$dbh->do("unlock tables");
		print	"<p>Aktualizováno: <b>$cnt</b> dat vzniku členství",
			($err ? "<br>Počet chyb (nezměněno): <b>$err</b>" : ''),"</p>\n";
		print "<p>Nelze aktualizovat <b>$err1</b> dat vzniku členství</p>" if($err1);
		print "<p>Vloženo <b>$err2</b> dat vzniku členství, bude nutné doplnit",
			" další údaje u těchto členů</p>" if($err2);
		}
	else
		{
		my ($id,$name,$fullname,$dat,$type,$group,$clenid);
		$dbh->do("lock tables `phpbb_user_group` read,`phpbb_users` read,
			`phpbb_groups` read,`phpbb_profile_fields_data` read");
		my $sth=$dbh->prepare("SELECT `phpbb_users`.`user_id`,`username`,
					`pf_fullname`,`pf_vznikclenstvi`,`user_type`,
					`group_name`,`pf_idclena`
				FROM `phpbb_user_group`
				LEFT JOIN `phpbb_users`
					ON(`phpbb_users`.`user_id`=`phpbb_user_group`.`user_id`)
				LEFT JOIN `phpbb_groups`
					ON(`phpbb_groups`.`group_id`=`phpbb_user_group`.`group_id`)
				LEFT JOIN `phpbb_profile_fields_data`
					ON(`phpbb_profile_fields_data`.`user_id`=`phpbb_users`.`user_id`)
#				WHERE `phpbb_user_group`.`group_id`=$idkraj
				WHERE FIND_IN_SET(`phpbb_user_group`.`group_id`,'$set')
				ORDER BY 6,2");
		$sth->execute() or die $sth->errstr;
		$sth->bind_columns(\($id,$name,$fullname,$dat,$type,$group,$clenid));
		print	"<input type='hidden' name='kraj' value='$idkraj'>\n",
			"<table><caption class='norm'>",$sth->rows," členů</caption>\n",
			"<tr class='hdr'>",
			"<td>Číslo</td><td>Člen</td><td>Plné jméno</td><td>Členem od</td>",
			($set=~m/,/ ? "<td>Kraj</td>" : ''), 
			"</tr>\n";
		while ($sth->fetch)
			{
			$fullname.=' ' unless($fullname);
			$dat=~s/\s//g;
			my ($den,$mes,$rok)=split(/\-/,$dat);
			my $datum=sprintf("%02d.%02d.%04d",$den,$mes,$rok);
			if($type==1 or $type==2)
				{
				my $t=($type==1 ? 'inactive' : 'bot');
				print	"<tr class='bgred'><td class='ri'>$clenid</td><td>$name</td>",
					"<td>$fullname ($t)</td>",
					"<td>$datum</td>",
					($set=~m/,/ ? "<td>$group</td>" : ''), 
					"</tr>\n";
				}
			else
				{
				print	"<tr><td class='ri'>$clenid</td><td>$name</td>",
					"<td>$fullname</td>",
					"<td>";
				if($access[1] or $grpaccess[2])
					{
					print	"<input maxlength=10 class='datum' type='text' name='d_$id' value='",
						$datum,"'>";
					}
				else
					{
					print $datum;
					}
				print	"</td>",
					($set=~m/,/ ? "<td>$group</td>" : ''), 
					"</tr>\n";
				}
			}
		$sth->finish;
		$dbh->do("unlock tables");
		if($access[1] or $grpaccess[2])
			{
			print "<tr><th colspan=",($set=~m/,/ ? 5 : 4),"><input name='ok' type='submit' value='Uložit změny'></th></tr>\n";
			}
		print	"</table>\n";
		}
	}
else
	{
	print "<p>";
	if($access[0] or $access[1] or $hipriv)
		{
		&kraje(0);
		}
	elsif($grpaccess[0] or $grpaccess[2])
		{
		&kraje((krajclena())[1]);
		}
	print	"&nbsp;&nbsp;<input type='submit' value='Zobrazit'></p>\n";
	}
print	"</form>\n";
}

sub jmena
{
my $idkraj=param('kraj')*1;
my $set=($idkraj==-1 ? get_setup('ksgroups','string') : $idkraj);
print	"<h2>Plná jména členů ",ukaz_kraj($idkraj),"</h2>",
	"<form action='index.cgi' method='post'>\n",
#join(',',@grpaccess),
	"<input type='hidden' name='fce' value='1'>\n";
if($method eq 'post')
	{
	if(param('ok') and ($access[1] or $grpaccess[2]))
		{
		my $cnt=0;
		if($iswin) {use utf8;}
		my @pars=param();
		my $sth=$dbh->prepare("update `phpbb_profile_fields_data` set
					`pf_fullname`=?
				where `user_id`=?");
		my $sth1=$dbh->prepare("insert into `phpbb_profile_fields_data` set
					`pf_fullname`=?,`user_id`=?");
		$dbh->do("lock tables `phpbb_profile_fields_data` write");
		my ($err1, $err2,$names)=(0,0,'');
		foreach my $p(@pars)
			{
			next if(substr($p,0,2) ne 'n_');
			my $ok=1;
			my $id=substr($p,2)*1;
			my $fn=param($p);
			if(find_id($id))
				{
				$sth->execute($fn,$id) or $ok=0;
				$sth->finish;
				$err1++ unless($ok);
				}
			else
				{
				$sth1->execute($fn,$id) or $ok=0;
				$sth1->finish;
				unless($ok)
					{
					$err2++;
					$names.=$fn . "<br>";
					}
				}
			$cnt++ if($ok);
			}
		$dbh->do("unlock tables");
#		if($iswin) {no utf8;}
		print "<p>Aktualizováno <b>$cnt</b> plných jmen členů</p>";
		print "<p>Nelze aktualizovat <b>$err1</b> plných jmen členů</p>" if($err1);
		print "<p>Vloženo <b>$err2</b> plných jmen členů, bude nutné doplnit",
			" další údaje u těchto členů:<br><b>$names</b></p>" if($err2);
		}
	else
		{
		my ($id,$name,$fullname,$type,$group,$clenid);
		$dbh->do("lock tables `phpbb_profile_fields_data` read,
			`phpbb_user_group` read, `phpbb_users` read, `phpbb_groups` read");
		my $sth=$dbh->prepare("SELECT `phpbb_user_group`.`user_id`,`username`,
					`pf_fullname`,`user_type`,`group_name`,
					`pf_idclena`
				FROM `phpbb_user_group`
				LEFT JOIN `phpbb_users`
					ON(`phpbb_users`.`user_id`=`phpbb_user_group`.`user_id`)
				LEFT JOIN `phpbb_groups`
					ON(`phpbb_groups`.`group_id`=`phpbb_user_group`.`group_id`) 
				LEFT JOIN `phpbb_profile_fields_data`
					ON(`phpbb_profile_fields_data`.`user_id`=`phpbb_users`.`user_id`)
#				WHERE `phpbb_user_group`.`group_id`=$idkraj
				WHERE FIND_IN_SET(`phpbb_user_group`.`group_id`,'$set')
				ORDER BY 5,2");
		$sth->execute() or do_die($sth->errstr);
		$sth->bind_columns(\($id,$name,$fullname,$type,$group,$clenid));
		print	"<input type='hidden' name='kraj' value='$idkraj'>\n",
			"<table><caption class='norm'>",$sth->rows," členů</caption>\n",
			"<tr class='hdr'>",
			"<td>Číslo</td><td>Člen</td><td>Plné jméno</td>",
			($set=~m/,/ ? "<td>Kraj</td>" : ''),
			"</tr>\n";
		if($iswin) {use utf8;}
		while ($sth->fetch)
			{
			$fullname.=' ' unless($fullname);
			if($type==1 or $type==2)
				{
				my $t=($type==1 ? 'inactive' : 'bot');
				print	"<tr class='bgred'><td class='ri'>$clenid</td><td>$name</td>",
					"<td>$fullname ($t)</td>",
					($set=~m/,/ ? "<td>$group</td>" : ''),
					"</tr>\n";
				}
			else
				{
				print	"<tr><td class='ri'>$clenid</td><td>$name</td>",
					"<td>";
				if($access[1] or $grpaccess[2])
					{
					print "<input maxlength=255 class='fname' type='text' name='n_$id' value='$fullname'>";
					}
				else
					{
					print $fullname;
					}
				print	"</td>",
					($set=~m/,/ ? "<td>$group</td>" : ''),
					"</tr>\n";
				}
			}
		$sth->finish;
		$dbh->do("unlock tables");
		if($access[1] or $grpaccess[2])
			{
			print "<tr><th colspan=",($set=~m/,/ ? 4 : 3),"><input name='ok' type='submit' value='Uložit změny'></th></tr>\n";
			}
		print	"</table>\n";
		}
	}
else
	{
	print "<p>";
	if($access[0] or $access[1] or $hipriv)
		{
		&kraje(0);
		}
	elsif($grpaccess[0] or $grpaccess[2])
		{
		&kraje((krajclena())[1]);
		}
	print	"&nbsp;&nbsp;<input type='submit' value='Zobrazit'></p>\n";
	}
print	"</form>\n";
}

sub ukaz_skupinu
{
my $s=shift;
my $skup;
my $sth=$dbh->prepare("select `group_name` from `phpbb_groups`
			WHERE `group_id`=$s");
$sth->execute() or die $sth->errstr;
($skup)=$sth->fetchrow_array;
$sth->finish;
$skup=' - ' . $skup if($skup);
return $skup;
}

sub ukaz_kraj
{
my $k=shift;
my $kraj;
if($k==-1)
	{
	$kraj='všechny kraje';
	}
else
	{
	my $sth=$dbh->prepare("select `group_name` from `phpbb_groups`
				WHERE `group_id`=$k");
	$sth->execute() or die $sth->errstr;
	($kraj)=$sth->fetchrow_array;
	$sth->finish;
	}
$kraj=' - ' . $kraj if($kraj);
return $kraj;
}

sub castky
{
my $idkraj=param('kraj')*1;
my $set=($idkraj==-1 ? get_setup('ksgroups','string') : $idkraj);
print	"<h2>Členské příspěvky ",ukaz_kraj($idkraj),"</h2>",
	"<form action='index.cgi' method='post'>\n",
	"<input type='hidden' name='fce' value='3'>\n";
if($method eq 'post')
	{
	if(param('ok'))
		{
		my $cnt=my $err=0;
		my @pars=param();
		my $sth=$dbh->prepare("update `phpbb_profile_fields_data` set
					`pf_datumclprispevku`=?,
					`pf_vyseclprispevku`=?,
					`pf_dalsiclprispevek`=?
				where `user_id`=?");
		my $sth1=$dbh->prepare("select date(?)");
		my $sth2=$dbh->prepare("select `pf_datumclprispevku`
					from `phpbb_profile_fields_data`
					where `user_id`=?");
		my $sth3=$dbh->prepare("insert into `phpbb_profile_fields_data` set
					`pf_datumclprispevku`=?,
					`pf_vyseclprispevku`=?,
					`pf_dalsiclprispevek`=?
				where `user_id`=?");
		$dbh->do("lock tables `phpbb_profile_fields_data` write");
		my ($err1, $err2,$names)=(0,0,'');
		foreach my $p(@pars)
			{
			next if(substr($p,0,2) ne 'd_');
			my $id=substr($p,2)*1;
			my $dat=param($p);
			$dat=~s/\s//g;
			my $ddat=param("n_$id");
			$ddat=~s/\s//g;
			my ($den,$mes,$rok,$dden,$dmes,$drok,$castka);
			$castka=param("c_$id")*1;
			if($dat=~m/^(\d{1,2}).(\d{1,2}).(\d{1,4})$/)
				{
				($den,$mes,$rok)=($1,$2,$3);
				$rok+=2000 if($rok < 100 and $rok > 0);
				$dat=sprintf("%2d-%2d-%4d",$den,$mes,$rok);
				unless($rok==0 and $mes==0 and $den==0)
					{
					$sth1->execute("$rok-$mes-$den") or do_die($sth1->errstr);
					my ($d)=$sth1->fetchrow_array;
					$sth1->finish;
					unless($d*1)
						{
						$err++;
						$sth2->execute($id) or do_die($sth2->errstr);
						($dat)=$sth2->fetchrow_array;
						$sth2->finish;
						}
					}
				}
			if($ddat=~m/^(\d{1,2}).(\d{1,2}).(\d{1,4})$/)
				{
				($dden,$dmes,$drok)=($1,$2,$3);
				$drok+=2000 if($drok < 100 and $drok > 0);
				$ddat=sprintf("%2d-%2d-%4d",$dden,$dmes,$drok);
				unless($drok==0 and $dmes==0 and $dden==0)
					{
					$sth1->execute("$drok-$dmes-$dden") or do_die($sth1->errstr);
					my ($d)=$sth1->fetchrow_array;
					$sth1->finish;
					unless($d*1)
						{
						$err++;
						$sth2->execute($id) or do_die($sth2->errstr);
						($ddat)=$sth2->fetchrow_array;
						$sth2->finish;
						}
					}
				}
			my $ok=1;
			if(find_id($id))
				{
				$sth->execute($dat,$castka,$ddat,$id) or $ok=0;
				$sth->finish;
				$err1++ unless($ok)
				}
			else
				{
				$sth3->execute($dat,$id) or $ok=0;
				$sth3->finish;
				$err2++ unless($ok);
				}
			$cnt++ if($ok);
			}
		$dbh->do("unlock tables");
		print	"<p>Aktualizovány údaje o <b>$cnt</b> členech",
			($err ? "<br>Počet chyb (nezměněno): <b>$err</b>" : ''),"</p>\n";
		print "<p>Nelze aktualizovat <b>$err1</b> údajů o členech</p>" if($err1);
		print "<p>Vloženo <b>$err2</b> údajů o členech, bude nutné doplnit",
			" další údaje u těchto členů</p>" if($err2);
		}
	else
		{
		my ($id,$name,$fullname,$datum,$castka,$dalsi,$clenstvi,$group,$clenid);
		$dbh->do("lock tables `phpbb_user_group` read,`phpbb_users` read,
			`phpbb_profile_fields_data` read,`phpbb_groups` read"); 
		my $sth=$dbh->prepare("SELECT `phpbb_users`.`user_id`,`username`,
					`pf_fullname`,`pf_datumclprispevku`,
					`pf_vyseclprispevku`,`pf_dalsiclprispevek`,
					`pf_vznikclenstvi`,`group_name`,`pf_idclena`
			FROM `phpbb_user_group`
			LEFT JOIN `phpbb_users`
				ON(`phpbb_users`.`user_id`=`phpbb_user_group`.`user_id`)
			LEFT JOIN `phpbb_groups`
					ON(`phpbb_groups`.`group_id`=`phpbb_user_group`.`group_id`)
			LEFT JOIN `phpbb_profile_fields_data`
				ON(`phpbb_profile_fields_data`.`user_id`=`phpbb_users`.`user_id`)
#			WHERE `phpbb_user_group`.`group_id`=?
			WHERE FIND_IN_SET(`phpbb_user_group`.`group_id`,'$set')
			ORDER BY 8,2");
		$sth->execute($idkraj) or die $sth->errstr;
		$sth->bind_columns(\($id,$name,$fullname,$datum,$castka,$dalsi,$clenstvi,$group,$clenid));
		print	"<input type='hidden' name='kraj' value='$idkraj'>\n",
			"<table><caption class='norm'>",$sth->rows," členů</caption>\n",
			"<tr class='hdr'><td>Číslo</td><td>Člen</td><td>Plné jméno</td>",
			"<td>Členství</td>",
			"<td>Zaplaceno</td><td>Částka</td><td>Příští platba</td>",
			($set=~m/,/ ? "<td>Kraj</td>" : ''),
			"</tr>\n";
		while($sth->fetch)
			{
			$clenstvi=~s/\s//g;
			$datum=~s/\s//g;
			$dalsi=~s/\s//g;
			my ($den,$mes,$rok)=split(/\-/,$datum);
			my ($dden,$dmes,$drok)=split(/\-/,$dalsi);
			my ($cden,$cmes,$crok)=split(/\-/,$clenstvi);
			$fullname.=' ' unless($fullname);
			print	"<tr><td class='ri'>$clenid</td><td>$name</td>",
				"<td>$fullname</td>",
				"<td>",sprintf("%02d.%02d.%04d",$cden,$cmes,$crok),"</td>",
				"<td>";
			if($access[1] or $grpaccess[2])
				{
				print	"<input maxlength=10 class='datum' type='text' name='d_",$id*1,"' value='",
					sprintf("%02d.%02d.%04d",$den,$mes,$rok),"'>";
				}
			else
				{
				printf("%02d.%02d.%04d",$den,$mes,$rok);
				}
			print	"</td>";
			if($access[1] or $grpaccess[2])
				{
				print	"<td><input maxlength=4 class='castka' type='text' name='c_",$id*1,"' value='",
					$castka*1,"'>";
				}
			else
				{
				print "<td style='text-align: right'>",$castka*1;
				}
			print	"</td><td>";
			if($access[1] or $grpaccess[2])
				{
				print	"<input maxlength=10 class='datum' type='text' name='n_",$id*1,"' value='",
					sprintf("%02d.%02d.%04d",$dden,$dmes,$drok),"'>";
				}
			else
				{
				printf("%02d.%02d.%04d",$dden,$dmes,$drok);
				}
			print	"</td>",($set=~m/,/ ? "<td>$group</td>" : ''),"</tr>\n";
			}
		$sth->finish;
		$dbh->do("unlock tables");
		if($access[1] or $grpaccess[2])
			{
			print "<tr><th colspan=",($set=~m/,/ ? 8 : 7),"><input name='ok' type='submit' value='Uložit změny'></th></tr>\n";
			}
		print	"</table>\n";
		}
	}
else
	{
	print "<p>";
	if($access[0] or $access[1] or $hipriv)
		{
		&kraje(0);
		}
	elsif($grpaccess[0] or $grpaccess[2])
		{
		&kraje((krajclena())[1]);
		}
	print	"&nbsp;&nbsp;<input type='submit' value='Zobrazit'></p>\n";
	}
print	"</form>\n";
}

sub import
{
if($method eq 'post')
	{
	my ($acnt,$ecnt,$ncnt,$cnt)=(0,0,0,0);
	my $sth=$dbh->prepare("select `user_id`,`pf_vznikclenstvi`
				from `phpbb_profile_fields_data`
				where `pf_fullname`=?");
	my $sth1=$dbh->prepare("update `phpbb_profile_fields_data` set
				`pf_vznikclenstvi`=?
				where `user_id`=?");
	my $data=param('data');
	my @rows=split(/\n/,$data);
	my $notfound='';
	foreach my $row(@rows)
		{
		$row=~s/\n//g;
		$row=~s/^\s+|\s+$//g;
		my ($funkce,$jmeno,$prijmeni,$datum)=split(/\t/,$row);
		if($funkce eq 'Funkce' or length($row)==0)
			{
			next;
			}
		elsif($datum !~ m/^\d/)
			{
			$datum=$prijmeni;
			$prijmeni=$jmeno;
			$jmeno=$funkce;
			}
		my ($den,$mes,$rok)=split(/\./,$datum);
		$rok+=2000;
		$cnt++;
#		print "<br>$jmeno $prijmeni";
		my $jm="$jmeno $prijmeni";
		$sth->execute($jm) or die $sth->errstr;
		if($sth->rows)
			{
			my ($id,$dat)=$sth->fetchrow_array();
			if($dat)
				{
				$dat=~s/\s//g;
				my ($oden,$omes,$orok)=split(/\-/,$dat);
				if($oden != $den or $omes != $mes or $orok != $rok)
					{
					my $d=sprintf("%2d-%2d-%4d",$den,$mes,$rok);
					$sth1->execute($d,$id) or die $sth1->errstr;
					$sth1->finish;
					$acnt++;
					}
				else
					{
					$ncnt++;
					}
				}
			}
		else
			{
#			print " - $jmeno $prijmeni";
			$notfound.="<br>$jmeno $prijmeni $datum\n";
#print "<br>$notfound";
			$ecnt++;
			}
		$sth->finish;
		}
	print	"<p>Aktualizováno: ",$acnt*1,
		"<br>Nezměněno: ",$ncnt*1,
		"<br>Počet chyb: ",$ecnt*1,
		"<br><b>Celkem: ",$cnt*1,
      		"</b></p>\n";
	print "<p><b>Nelze aktualizovat:</b>$notfound</p>\n";
	}
else
	{
	print	"<h2>Import data registrace členů</h2>",
		"Vlož tabulku z <a href='http://www.ceskapiratskastrana.cz/wiki/ao:seznam_clenu' ",
		"title='Seznam členů' target='_blank'><b>wiki</b></a> pomocí Copy&Paste.",
		"<br>(zaber i hlavičku tabulky)",
		"<form action='index.cgi' method='post'>\n",
		"<input type='hidden' name='fce' value='9'>\n",
		"<p><textarea id='dd' name='data' rows=20 cols=50></textarea>",
		"<br><input type='submit' value='Zapsat'></p>\n",
		"</form>\n",
		"<script type='text/javascript'>document.getElementById('dd').focus();</script>\n";
		}
}

sub htmlstart
{
# html header
print <<"EOF";
Cache-Control: no-cache, no-store, no-transform, must-revalidate
Pragma: no-cache
Content-type: text/html

<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<meta http-equiv="Content-language" content="cs">
<meta http-equiv="Cache-control" content="no-cache">
<meta name="pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
<meta http-equiv="Content-language" content="cs">
<title>Evidence členů</title>
<link rel="Stylesheet" href="style.css">
<link rel="shortcut icon" href="/favicon.png"  type="image/x-icon">
<script type="text/javascript">
function refrchk(but1,but2)
{
p=document.getElementById(but1);
s=document.getElementById(but2);
if(p.value=="on")
	{
	s.disabled="";
	}
else
	{
	s.checked="";
	s.disabled="true";
	}
}
function dinput(id)
{
document.getElementById(id).disabled="true";
}
function einput(id)
{
i=document.getElementById(id);
i.disabled="";
i.focus();
}
</script>
</head>
<body>
EOF
}

sub skupiny
{
my ($prokraj,$blank)=@_;
my ($gid,$skup,$sth);
my $set=get_setup('groups_to_log','text');
#if($prokraj)
#	{
#	}
#else
#	{
	$sth=$dbh->prepare("SELECT `group_id`,`group_name`
		FROM `phpbb_groups`
		WHERE FIND_IN_SET(`group_id`,'$set')
		GROUP BY `group_id`
		ORDER BY `group_name`");
	$sth->execute() or die $sth->errstr;
#	}
$sth->bind_columns(\($gid,$skup));
print	"<select name='skupina' size=1>\n";
while ($sth->fetch)
	{
#	next if($prokraj > 0 and $prokraj!=$gid);
	print "<option value=$gid>$skup</option>\n";
	}
$sth->finish;
print "</select>";
}

sub kraje
{
my $prokraj=shift;
my ($gid,$kraj);
my $idkraj=param('kraj')*1;
my $ksgroups=get_setup('ksgroups','string');
my $sth=$dbh->prepare("SELECT `group_id`,`group_name` from `phpbb_groups`
			WHERE FIND_IN_SET(`group_id`,?)
			ORDER BY `group_name`");
$sth->execute($ksgroups) or die $sth->errstr;
$sth->bind_columns(\($gid,$kraj));
print	"<select name='kraj' size=1>\n";
if($prokraj*1==0)
	{
	print	"<option value=-1",($idkraj==-1 ? ' selected' : ''),
		">všechny kraje</option>\n";
	}
while ($sth->fetch)
	{
	next if($prokraj > 0 and $prokraj!=$gid);
	print "<option value=$gid",($idkraj==$gid ? ' selected' : ''),
		">$kraj</option>\n";
	}
$sth->finish;
print "</select>";
}

sub regpkraje
{
my $prokraj=shift;
my ($gid,$kraj);
my $idkraj=param('kraj')*1;
my $rgroups=get_setup('regp_groups','string');
my $sth=$dbh->prepare("SELECT `group_id`,`group_name` from `phpbb_groups`
			WHERE FIND_IN_SET(`group_id`,?)
			ORDER BY `group_name`");
$sth->execute($rgroups) or die $sth->errstr;
$sth->bind_columns(\($gid,$kraj));
print	"<select name='kraj' size=1>\n";
if($prokraj*1==0)
	{
	print	"<option value=-1",($idkraj==-1 ? ' selected' : ''),
		">všechny kraje</option>\n";
	}
while ($sth->fetch)
	{
	next if($prokraj > 0 and $prokraj!=$gid);
	print "<option value=$gid",($idkraj==$gid ? ' selected' : ''),
		">$kraj</option>\n";
	}
$sth->finish;
print "</select>";
}

sub find_id
{
my $id=shift;
$id*=1;
my $sth=$dbh->prepare("select count(*) from `phpbb_profile_fields_data`
			where `user_id`=?");
$sth->execute($id) or die $sth->errstr;
my ($c)=$sth->fetchrow_array;
$sth->finish;
return $c;
}

sub do_die
{
my $err=shift;
$dbh->do("unlock tables");
die $err;
}

sub lecit
{
my $lecitprm=shift;
return '' if(length($lecitprm)==0);
$lecitprm=~s/\;\s*(drop|alter|truncate)\s+table\s+//sgi;
$lecitprm=~s/\;\s*drop\s+database\s+//sgi;
$lecitprm=~s/\;\s*delete\s+from\s+//sgi;
$lecitprm=~s/\;\s*insert\s+into\s+//sgi;
$lecitprm=~s/\;\s*(update|replace)\s+//sgi;
return $lecitprm; 
}

sub phpbb_check_hash
{
my ($password, $hash)=@_;
my $itoa64 = './0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz';
if(length($hash) == 34)
	{
	return (_hash_crypt_private($password, $hash, $itoa64) eq $hash);
	}
return (md5_hex($password) == $hash);
}

sub _hash_crypt_private
{
my ($password, $setting, $itoa64)=@_;
my $output = '*';
if (substr($setting, 0, 3) != '$H$')
	{
	return $output;
	}
my $count_log2 = index($itoa64,substr($setting,3,1));
if ($count_log2 < 7 || $count_log2 > 30)
	{
	return $output;
	}
my $count = 1 << $count_log2;
my $salt = substr($setting, 4, 8);
if(length($salt) != 8)
	{
	return $output;
	}
my $hash = pack('H*', md5_hex($salt . $password));
while($count)
	{
	$hash = pack('H*', md5_hex($hash . $password));
	$count--;
	}
$output = substr($setting, 0, 12);
$output .= _hash_encode64($hash, 16, $itoa64);
return $output;
}

sub _hash_encode64
{
my ($input, $count, $itoa64)=@_;
my $output = '';
my $i = 0;
while ($i < $count)
	{
	my $value = ord(substr($input,$i,1));
	$i++;
	$output .= substr($itoa64,($value & 0x3f),1);

	if ($i < $count)
		{
		$value |= ord(substr($input,$i,1)) << 8;
		}

	$output .= substr($itoa64,(($value >> 6) & 0x3f),1);

	if ($i++ >= $count)
		{
		last;
		}

	if ($i < $count)
		{
		$value |= ord(substr($input,$i,1)) << 16;
		}

	$output .= substr($itoa64,(($value >> 12) & 0x3f),1);

	if ($i++ >= $count)
		{
		last;
		}

	$output .= substr($itoa64,(($value >> 18) & 0x3f),1);
	}
return $output;
}

sub login
{
my $error='';
if($method eq 'post' and param('user') and param('pass'))
	{
	my ($id,$hash);
	$user=lecit(param('user'));
	my $pass=lecit(param('pass'));
	my $sth=$dbh->prepare("select `user_id`,`user_password` from `phpbb_users`
			where `username` like ?");
	$sth->execute($user) or die $sth->errstr;
	$sth->bind_columns(\($id,$hash));
	unless($sth->rows)
		{
		$sth->finish;
		$error="<p class='red'><b>Přihlašovací jméno nebylo nalezeno</b></p>";
		goto LOGIN;
		}
	$sth->fetch;
	$sth->finish;
	unless(phpbb_check_hash($pass,$hash))
		{
		$error="<p class='red'><b>Chybné heslo</b></p>";
		goto LOGIN;
		}
	$userid=$id;
	$adminhash=$hash;
	my $kuky=new CGI::Cookie(-name => 'ao_admin',
				-value => [$user,md5_hex($hash,$user)],
				-expires => '+' . $logout*1 . 'h',
#				-secure => 1
				);
	print "Set-Cookie: $kuky\n";
	&htmlstart;
	&mymenu;
	return;
	}
elsif($ARGV[0] ne 'logout' and check_cookies())
	{
	&htmlstart;
	&mymenu;
	return;
	}
LOGIN:
$user='';
$userid=$fce=0;
my $kuky=new CGI::Cookie(-name => 'ao_admin',
			-value => ['',''],
			-expires => '+' . $logout*1 . 'h',
#			-secure => 1
			);
print "Set-Cookie: $kuky\n";
&htmlstart;
print	"<div id='adminmenu'>",
	"<form action='index.cgi' method='post'>",
	"Přihlášení&nbsp;&nbsp;<b>Jméno:</b>",
	"<input id='user' type='text' name='user' title=\"Zapiš jméno a příjmení bez diakritiky, oddělené mezerou.\nPrvní písmeno jména i příjmení musí být velké.\">",'&nbsp;'x2,
	"<b>Heslo:</b><input type='password' name='pass' title=\"Zapiš heslo jako do fóra\">",'&nbsp;'x2,
	"<input type='submit' name='login' value='Přihlásit se'>",
	"<br><small><i>(Jméno a příjmení s velkým písmenem na začátku a bez diakritiky)</i></small>",
	"</form>",
	"</div>\n",
	"<h1 style='text-align: center'>Evidence členů - administrace</h1>\n$error",
	"<p class='cent'>Nápověda se zobrazí po podržení myši nad ovládacím prvkem nebo polem.",
	"<br>Pokud někde nápověda chybí, tak mi dejte vědět na <a href='mailto:petr.vileta\@ceskapiratskastrana.cz' title='Petr Vileta'>stranický mail</a>.",
	"<br><br>Všechny údaje jsou přebírány z profilů ve fóru phpbb, kromě dokumentů (souborů).",
	"<br>Některé údaje nejdou v profilu člena editovat, ani nejsou zobrazené.",
	"<br>Pokud nemůžete údaje editovat, zkuste požádat o příslušná oprávnění ",
	"<a href='https://www.ceskapiratskastrana.cz/forum/viewforum.php?f=227' target='_blank' title='Podatelna AO'>administrativní odbor</a>.</p>\n",
	"<script type='text/javascript'>document.getElementById('user').focus();</script>";
}

sub checkdocaccess
{
my $fileid=1 * shift;
# je prihlaseny uzivatel ve skupine Evidence?
my $aogroup=get_setup('ao_group','number');
my $sth=$dbh->prepare("select count(*) from `phpbb_user_group`
		where user_id=? and group_id=?");
$sth->execute($userid,$aogroup) or die $sth->errstr;
my ($ok)=$sth->fetchrow_array;
if($ok)
	{
	$sth->finish;
	return 1;
	}
my ($group,$lead);
# hledej opravneneho uzivatele
$sth=$dbh->prepare("select FIND_IN_SET(?,`smi_menit`)
		from `evidence_dokumenty`
		where `id`=?");
my $usr=sprintf("U%01d",$userid);
$sth->execute($usr,$fileid) or die $sth->errstr;
($ok)=$sth->fetchrow_array;
if($ok)
	{
	$sth->finish;
	return 1;
	}
# hledej opravnenou beznou skupinu
my $sth2=$dbh->prepare("select `group_id`,`group_leader`
			from `phpbb_user_group`
			where `user_id`=?");
$sth2->execute($userid) or die $sth2->errstr;
$sth2->bind_columns(\($group,$lead));
while ($sth2->fetch)
	{
	$usr=sprintf("G%01d",$group);
	$sth->execute($usr,$fileid) or die $sth->errstr;
	($ok)=$sth->fetchrow_array;
	if(!$ok and $lead)
		{
		$usr=sprintf("G%01dL",$group); # hledej leadera skupiny
		$sth->execute($usr,$fileid) or die $sth->errstr;
		($ok)=$sth->fetchrow_array;
		}
	last if($ok);
	}
$sth2->finish;
return $ok;
}

sub checkaccess
{
my ($funkce,$pravo)=@_;
my ($sth1,$sth2,$sth3,$group,$lead,$ret);
@access=(0,0);
@grpaccess=(0,0,0,0);
$ret=$hipriv=0;
my $higroups=get_setup('hiprivgroups','string');
$sth1=$dbh->prepare("select FIND_IN_SET(?,`smi_videt`),FIND_IN_SET(?,`smi_menit`)
		from `evidence_prava`
		where funkce=?");
$sth2=$dbh->prepare("select `group_id`,`group_leader`
			from `phpbb_user_group`
			where `user_id`=?");
$sth3=$dbh->prepare("select `group_id`,`group_leader`
			from `phpbb_user_group`
			where `user_id`=? and FIND_IN_SET(`group_id`,?)");
# hledej opravneneho uzivatele
my $usr=sprintf("U%01d",$userid);
$sth1->execute($usr,$usr,$funkce) or die $sth1->errstr;
if($sth1->rows)
	{
	@access=$sth1->fetchrow_array();
	$sth1->finish;
	if($access[1])
		{
		$ret=1;
		}
	elsif($access[0] and $pravo ne 'w')
		{
		$ret=1;
		}
	}
# hledej opravnenou privilegovanou skupinu
$sth3->execute($userid,$higroups) or die $sth3->errstr;
$sth3->bind_columns(\($group,$lead));
while ($sth3->fetch)
	{
	$usr=sprintf("G%01d",$group);
	$sth1->execute($usr,$usr,$funkce) or die $sth1->errstr;
	if($sth1->rows)
		{
		($grpaccess[0],$grpaccess[2])=$sth1->fetchrow_array();
		$grpaccess[1]=$grpaccess[3]=0;
		if($grpaccess[2])
			{
			$grpaccess[2]=$group;
			$hipriv=1;
			$sth1->finish;
			$sth3->finish;
			$ret=1;
			last;
			}
		elsif($grpaccess[0] and $pravo ne 'w')
			{
			$grpaccess[0]=$group;
			$hipriv=1;
			$sth1->finish;
			$sth3->finish;
			$ret=1;
			last;
			}
		}
	if($lead)
		{
		$usr=sprintf("G%01dL",$group); # hledej skupinu
		$sth1->execute($usr,$usr,$funkce) or die $sth1->errstr;
		if($sth1->rows)
			{
			($grpaccess[0],$grpaccess[2])=$sth1->fetchrow_array();
			if($grpaccess[2])
				{
				$grpaccess[1]=$grpaccess[3]=1;
				$grpaccess[2]=$group;
				$hipriv=1;
				$sth1->finish;
				$sth3->finish;
				$ret=1;
				last;
				}
			elsif($grpaccess[0] and $pravo ne 'w')
				{
				$grpaccess[1]=$grpaccess[3]=1;
				$grpaccess[0]=$group;
				$hipriv=1;
				$sth1->finish;
				$sth3->finish;
				$ret=1;
				last;
				}
			}
		}
	}
$sth3->finish;
# hledej opravnenou beznou skupinu
$sth2->execute($userid) or die $sth2->errstr;
$sth2->bind_columns(\($group,$lead));
while ($sth2->fetch)
	{
	$usr=sprintf("G%01d",$group);
	$sth1->execute($usr,$usr,$funkce) or die $sth1->errstr;
	if($sth1->rows)
		{
		($grpaccess[0],$grpaccess[2])=$sth1->fetchrow_array();
		$grpaccess[1]=$grpaccess[3]=0;
		if($grpaccess[2])
			{
			$grpaccess[2]=$group;
			$sth1->finish;
			$sth2->finish;
			$ret=1;
			last;
			}
		elsif($grpaccess[0] and $pravo ne 'w')
			{
			$grpaccess[0]=$group;
			$sth1->finish;
			$sth2->finish;
			$ret=1;
			last;
			}
		}
	if($lead)
		{
		$usr=sprintf("G%01dL",$group); # hledej leadera skupiny
		$sth1->execute($usr,$usr,$funkce) or die $sth1->errstr;
		if($sth1->rows)
			{
			($grpaccess[0],$grpaccess[2])=$sth1->fetchrow_array();
			if($grpaccess[2])
				{
				$grpaccess[1]=$grpaccess[3]=1;
				$grpaccess[2]=$group;
				$sth1->finish;
				$sth2->finish;
				$ret=1;
				last;
				}
			elsif($grpaccess[0] and $pravo ne 'w')
				{
				$grpaccess[1]=$grpaccess[3]=1;
				$grpaccess[0]=$group;
				$sth1->finish;
				$sth2->finish;
				$ret=1;
				last;
				}
			}
		}
	}
$sth1->finish;
$sth2->finish;
return $ret;
}

sub checkfunc
{
my ($f,$r)=@_;
return 1 if(checkaccess($f,$r));
print "<h1 style='text-align: center' class='red'>Nemáte oprávnění</h1>";
return 0;
}

sub krajclena
{
my ($sth,$kraj,$grp,$ksgroups);
$kraj='';
$grp=0;
$ksgroups=get_setup('ksgroups','string');
$sth=$dbh->prepare("select `group_name`,`phpbb_groups`.`group_id`
		from `phpbb_groups`
		left join `phpbb_user_group`
			on (`phpbb_user_group`.`group_id`=`phpbb_groups`.`group_id`)
		where `user_id`=? and FIND_IN_SET(`phpbb_groups`.`group_id`,?)");
$sth->execute($userid,$ksgroups) or die $sth->errstr;
$sth->bind_columns(\($kraj,$grp));
if($sth->rows)
	{
	$sth->fetch;
	}
$sth->finish;
return wantarray ? ($kraj,$grp) : $kraj;
}

sub krajregp
{
my ($sth,$kraj,$grp,$rgroups);
$kraj='';
$grp=0;
$rgroups=get_setup('regp_groups','string');
$sth=$dbh->prepare("select `group_name`,`phpbb_groups`.`group_id`
		from `phpbb_groups`
		left join `phpbb_user_group`
			on (`phpbb_user_group`.`group_id`=`phpbb_groups`.`group_id`)
		where `user_id`=? and FIND_IN_SET(`phpbb_groups`.`group_id`,?)");
$sth->execute($userid,$rgroups) or die $sth->errstr;
$sth->bind_columns(\($kraj,$grp));
if($sth->rows)
	{
	$sth->fetch;
	}
$sth->finish;
return wantarray ? ($kraj,$grp) : $kraj;
}

sub setup_prava_aplikace
{
my ($funkce,$popis,$videt,$menit,$i,$sth,$nprava);
print	"<h2>Nastavení práv k aplikaci</h2>\n";
my %prava;
$sth=$dbh->prepare("select `funkce`,`popis`,`smi_videt`,`smi_menit`,substr(`funkce`,1,1) as `i`
			from `evidence_prava`
			order by `i`,`funkce`");
$sth->execute() or die $sth->errstr;
$sth->bind_columns(\($funkce,$popis,$videt,$menit,$i));
while ($sth->fetch)
	{
	%prava->{$funkce}->{popis}=$popis;
	%prava->{$funkce}->{videt}=$videt;
	if(param("acr_$funkce"))
		{
		%prava->{$funkce}->{videt}=param("acr_$funkce");
		}
	%prava->{$funkce}->{menit}=$menit;
	if(param("acw_$funkce"))
		{
		%prava->{$funkce}->{menit}=param("acw_$funkce");
		}
	}
if($method eq 'post')
	{
	if(param('vyber'))
		{
		$funkce=param('funkce')*1;
		if(param('komu') eq 'user')
			{
			if(param('access') eq 'r')
				{
				$videt=%prava->{$funkce}->{videt};
				$videt=~s/U\d+,*//g;
				%prava->{$funkce}->{videt}=$videt;
				}
			else
				{
				$menit=%prava->{$funkce}->{menit};
				$menit=~s/U\d+,*//g;
				%prava->{$funkce}->{menit}=$menit;
				}
			}
		elsif(param('komu') eq 'group')
			{
			if(param('access') eq 'r')
				{
				$videt=%prava->{$funkce}->{videt};
				$videt=~s/,*G\d+L*//g;
				%prava->{$funkce}->{videt}=$videt;
				}
			else
				{
				$menit=%prava->{$funkce}->{menit};
				$menit=~s/,*G\d+L*//g;
				%prava->{$funkce}->{menit}=$menit;
				}
			}
		}
	my @pars=param();
	foreach my $p(@pars)
		{
		if(substr($p,0,4) eq 'usr_')
			{
			$p=~m/^\D+_(\d+)$/;
			my $u=$1;
			$funkce=param('funkce');
			if(param('access') eq 'r')
				{
				%prava->{$funkce}->{videt}="U$u," . %prava->{$funkce}->{videt};
				}
			}
		elsif(substr($p,0,4) eq 'usw_')
			{
			$p=~m/^\D+_(\d+)$/;
			my $u=$1;
			$funkce=param('funkce');
			if(param('access') eq 'w')
				{
				%prava->{$funkce}->{menit}="U$u," . %prava->{$funkce}->{menit};
				}
			}
		elsif(substr($p,0,4) eq 'gnr_')
			{
			$p=~m/^\D+_(\d+)$/;
			my $g=$1;
			$funkce=param('funkce');
			if(param('access') eq 'r')
				{
				if(param("glr_$g"))
					{
					%prava->{$funkce}->{videt}=%prava->{$funkce}->{videt} . ",G$g" . 'L';
					}
				else
					{
					%prava->{$funkce}->{videt}=%prava->{$funkce}->{videt} . ",G$g";
					}
				}
			}
		elsif(substr($p,0,4) eq 'gnw_')
			{
			$p=~m/^\D+_(\d+)$/;
			my $g=$1;
			$funkce=param('funkce');
			if(param('access') eq 'w')
				{
				if(param("glw_$g"))
					{
					%prava->{$funkce}->{menit}=%prava->{$funkce}->{menit} . ",G$g" . 'L';
					}
				else
					{
					%prava->{$funkce}->{menit}=%prava->{$funkce}->{menit} . ",G$g";
					}
				}
			}
		}
	if(param('ok'))
		{
		$sth=$dbh->prepare("update `evidence_prava` set
					`smi_videt`=?,
					`smi_menit`=?
				where `funkce`=?");
		$dbh->do("lock tables `evidence_prava` write");
		foreach $funkce (sort keys %prava)
			{
			%prava->{$funkce}->{videt}=~s/,+/,/sgg;
			%prava->{$funkce}->{videt}=~s/^,+|,+$//sg;
			%prava->{$funkce}->{videt}=~s/(\d|L)(U|G)/$1,$2/sg;
			%prava->{$funkce}->{menit}=~s/,+/,/sg;
			%prava->{$funkce}->{menit}=~s/^,+|,+$//sg;
			%prava->{$funkce}->{menit}=~s/(\d|L)(U|G)/$1,$2/sg;
			$sth->execute(%prava->{$funkce}->{videt},%prava->{$funkce}->{menit},$funkce) or die $sth->errstr;
			}
		$sth->finish;
		$dbh->do("unlock tables");
		print "<p><br>&nbsp;<br><b>Uloženo</b></p>";
		return;
		}
	foreach my $p(@pars)
		{
		if(substr($p,0,4) eq 'cur_')
			{
			$funkce=substr($p,4) * 1;
			vyber_clena("- uživatelé s přístupem pro čtení",'r',$funkce,%prava);
			return;
			}
		elsif(substr($p,0,4) eq 'cuw_')
			{
			$funkce=substr($p,4) * 1;
			vyber_clena("- uživatelé s přístupem pro zápis",'w',$funkce,%prava);
			return;
			}
		elsif(substr($p,0,4) eq 'cgr_')
			{
			$funkce=substr($p,4) * 1;
			vyber_skupinu("- skupiny s přístupem pro čtení",'r',$funkce,%prava);
			return;
			}
		elsif(substr($p,0,4) eq 'cgw_')
			{
			$funkce=substr($p,4) * 1;
			vyber_skupinu("- skupiny s přístupem pro zápis",'w',$funkce,%prava);
			return;
			}
		}
	}
print	"<form action='index.cgi' method='post'>",
	"<input type='hidden' name='fce' value='$fce'>\n",
	"<table>\n",
	"<tr class='hdr'>",
	"<td>Funkce</td>",
	"<td>Název funkce</td>",
	"<td>Smí vidět</td>",
	"<td>Smí měnit</td>",
	"</tr>\n";
foreach $funkce (sort keys %prava)
	{
	print	"<tr><td class='top' style='text-align:right'><b>$funkce</b></td>\n",
		"<td class='top'>",%prava->{$funkce}->{popis},"</td>\n",
		"<td><div style='height: 12em; overflow-y: scroll; overflow-x: show; white-space: nowrap; margin: 0.2em 0 0.2em 0; width: 20em;'>";
	showusers('U',%prava->{$funkce}->{videt});
	showusers('G',%prava->{$funkce}->{videt});
	print "</div>",
		"<input type='hidden' name='acr_$funkce' value='",%prava->{$funkce}->{videt},"'>\n";
	if($access[1] or $grpaccess[2])
		{
		print	"<input type='submit' name='cur_$funkce' value='Členové'>",
			"&nbsp;&nbsp;<input type='submit' name='cgr_$funkce' value='Skupiny'>";
		}
	print	"</div></td>\n",
		"<td><div style='height: 12em; overflow-y: scroll; overflow-x: show; white-space: nowrap; margin: 0.2em 0 0.2em 0; width: 20em;'>";
	showusers('U',%prava->{$funkce}->{menit});
	showusers('G',%prava->{$funkce}->{menit});
	print "</div>",
		"<input type='hidden' name='acw_$funkce' value='",%prava->{$funkce}->{menit},"'>\n";
	if($access[1] or $grpaccess[2])
		{
		print	"<input type='submit' name='cuw_$funkce' value='Členové'>",
			"&nbsp;&nbsp;<input type='submit' name='cgw_$funkce' value='Skupiny'>";
		}
	print	"</div></td></tr>\n";
	}
$sth->finish;
if($access[1] or $grpaccess[2])
	{
	print	"<tr><th colspan=4><input style='font-weight: bold' name='ok' type='submit' value='Uložit změny'></th></tr>\n";
	}
print	"</table>\n</form>";
}

sub vyber_skupinu
{
my ($titulek,$typ,$funkce,%prava)=@_;
my ($sth,$groupid,$groupname,$pravo);
if($typ eq 'w')
	{
	$pravo=%prava->{$funkce}->{menit};
	}
else
	{
	$pravo=%prava->{$funkce}->{videt};
	}
#$pravo=~s/U\d+,*//g;
$pravo.=',';
print	"<h3>",%prava->{$funkce}->{popis}," $titulek</h3>\n",
	"<form action='index.cgi' method='post'>",
	"<input type='hidden' name='fce' value='$fce'>\n",
	"<input type='hidden' name='funkce' value='$funkce'>\n",
	"<input type='hidden' name='komu' value='group'>\n",
	"<input type='hidden' name='access' value='$typ'>\n";
print "<input type='hidden' name='id' value='",param('id'),"'>\n" if(param('id'));
print "<input type='hidden' name='kraj' value='",param('kraj'),"'>\n" if(param('kraj'));
print "<input type='hidden' name='file' value='",param('file'),"'>\n" if(param('file'));
foreach my $f (sort keys %prava)
	{
	if($f==$funkce and $typ eq 'r')
		{
		my $p=%prava->{$f}->{videt};
		$p=~s/,*G\d+L*//g;
		print	"<input type='hidden' name='acr_$f' value='$p'>\n";
		}
	else
		{
		print	"<input type='hidden' name='acr_$f' value='",%prava->{$f}->{videt},"'>\n";
		}
	if($f==$funkce and $typ eq 'w')
		{
		my $p=%prava->{$f}->{menit};
		$p=~s/,*G\d+L*//g;
		print	"<input type='hidden' name='acw_$f' value='$p'>\n";
		}
	else
		{
		print	"<input type='hidden' name='acw_$f' value='",%prava->{$f}->{menit},"'>\n";
		}
	}
print	"<table><tr class='hdr'>",
	"<td>Vybrat</td><td>Skupina</td><td>Jen vedoucí</td></tr>\n";
$sth=$dbh->prepare("select `group_id`,`group_name` from `phpbb_groups` order by `group_name`");
$sth->execute() or die $sth->errstr;
$sth->bind_columns(\($groupid, $groupname));
while ($sth->fetch)
	{
	my $but1="gn$typ" . "_$groupid";
	my $but2="gl$typ" . "_$groupid";
	print	"<tr>",
		"<td><input type='checkbox' name='$but1' id='$but1' ",
		"onclick=\"refrchk('$but1','$but2')\"",
		($pravo=~m/G$groupid\UL*,/ ? ' checked' : ''),"></td>",
		"<td>$groupname</td>",
		"<td><input type='checkbox' name='$but2' id='$but2'",
		($pravo=~m/G$groupid\UL,/ ? ' checked' : ''),
		($pravo=~m/G$groupid\UL*,/ ? '' : ' disabled'),"></td>",
		"</tr>\n";
	}
print "<tr><th colspan=3><input type='submit' name='vyber' value='Vybráno'></th></tr></table></form>\n";
$sth->finish;
}

sub vyber_clena
{
my ($titulek,$typ,$funkce,%prava)=@_;
my ($sth,$userid,$name,$fullname,$group1,$group2,$pravo);
my $forumgroup=get_setup('maingroup','number');
my $ksgroups=get_setup('ksgroups','string');
if($typ eq 'w')
	{
	$pravo=%prava->{$funkce}->{menit};
	}
else
	{
	$pravo=%prava->{$funkce}->{videt};
	}
$pravo.=',';
print	"<h3>",%prava->{$funkce}->{popis}," $titulek</h3>\n",
	"<form action='index.cgi' method='post'>",
	"<input type='hidden' name='fce' value='$fce'>\n",
	"<input type='hidden' name='funkce' value='$funkce'>\n",
	"<input type='hidden' name='komu' value='user'>\n",
	"<input type='hidden' name='access' value='$typ'>\n";
print "<input type='hidden' name='id' value='",param('id'),"'>\n" if(param('id'));
print "<input type='hidden' name='kraj' value='",param('kraj'),"'>\n" if(param('kraj'));
print "<input type='hidden' name='file' value='",param('file'),"'>\n" if(param('file'));
foreach my $f (sort keys %prava)
	{
	if($f==$funkce and $typ eq 'r')
		{
		my $p=%prava->{$f}->{videt};
		$p=~s/U\d+,*//g;
		print	"<input type='hidden' name='acr_$f' value='$p'>\n";
		}
	else
		{
		print	"<input type='hidden' name='acr_$f' value='",%prava->{$f}->{videt},"'>\n";
		}
	if($f==$funkce and $typ eq 'w')
		{
		my $p=%prava->{$f}->{menit};
		$p=~s/U\d+,*//g;
		print	"<input type='hidden' name='acw_$f' value='$p'>\n";
		}
	else
		{
		print	"<input type='hidden' name='acw_$f' value='",%prava->{$f}->{menit},"'>\n";
		}
	}
print	"<table><tr class='hdr'>",
	"<td>Vybrat</td><td>Člen</td><td>Plné jméno</td><td>Kraj</td></tr>\n";
$sth=$dbh->prepare("select `phpbb_users`.`user_id`,`phpbb_users`.`username_clean`,`phpbb_profile_fields_data`.`pf_fullname`,`phpbb_groups`.`group_name` as groups1,`groups1`.`group_name` as groups2
		from `phpbb_users`
		left join `phpbb_user_group` on (`phpbb_user_group`.`user_id`=`phpbb_users`.`user_id`)
		left join `phpbb_user_group` as group1 on (`group1`.`user_id`=`phpbb_users`.`user_id` and find_in_set(`group1`.`group_id`,?))
		left join `phpbb_profile_fields_data` on (`phpbb_profile_fields_data`.`user_id`=`phpbb_users`.`user_id`)
		left join `phpbb_groups` on (`phpbb_groups`.`group_id`=`phpbb_user_group`.`group_id`)
		left join `phpbb_groups` as groups1 on (`groups1`.`group_id`=`group1`.`group_id`)
		where `phpbb_user_group`.`group_id`=?
		order by `groups1`,`groups2`,`pf_fullname`");
$sth->execute($ksgroups,$forumgroup) or die $sth->errstr;
$sth->bind_columns(\($userid,$name,$fullname,$group1, $group2));
while ($sth->fetch)
	{
	print	"<tr>",
		"<td><input type='checkbox' name='us$typ","_$userid'",
		($pravo=~m/U$userid,/ ? ' checked' : ''),"></td>",
		"<td>$name</td><td>$fullname</td>",
		"<td>",(length($group2)==0 ? $group1 : $group2),"</td>",
		"</tr>\n";
	}
print "<tr><th colspan=4><input type='submit' name='vyber' value='Vybráno'></th></tr></table></form>\n";
$sth->finish;
}

sub showusers
{
my ($typ,$kdo)=@_;
my %typy=("U" => 'člen',
       "G" => 'skupina',
       "GL" => 'jen vedoucí',
       "R" => 'RegP');
my $sth;
if($typ eq 'U')
	{
	$sth=$dbh->prepare("select `pf_fullname` from `phpbb_users`
			left join `evidence_setup` on (`evidence_setup`.`name`='ksgroups')
			left join `phpbb_profile_fields_data` on (`phpbb_profile_fields_data`.`user_id`=`phpbb_users`.`user_id`)
			left join `phpbb_user_group` on (`phpbb_user_group`.`user_id`=`phpbb_users`.`user_id` and FIND_IN_SET(`phpbb_user_group`.`group_id`,`string`))
			where `phpbb_users`.`user_id`=?
			order by 1");
	}
elsif($typ eq 'G')
	{
#	$sth=$dbh->prepare("select `group_name` from `phpbb_groups`
#			left join `evidence_setup` on (`evidence_setup`.`name`='ksgroups')
#			where `group_id`=? and FIND_IN_SET(`phpbb_groups`.`group_id`,`string`)");
	$sth=$dbh->prepare("select `group_name` from `phpbb_groups`
			where `group_id`=?
			order by 1");
	}
while($kdo=~s/$typ(\d+)(L*),*//)
	{
	my $subtyp=($2 eq 'L' ? $typ . 'L' : $typ);
	$sth->execute($1) or die $sth->errstr;
	if($sth->rows)
		{
		my $name=$sth->fetchrow_array();
		if($typ eq 'U')
			{
			print "<nobr><b>$name</b> <i>(",%typy->{$subtyp},")</i></nobr><br>";
			}
		elsif($subtyp eq 'GL')
			{
			print "<nobr>$name <i>(<b>",%typy->{$subtyp},"</b>)</i></nobr><br>";
			}
		else
			{
			print "$name<br>";
			}
		$sth->finish;
		}
	}
}

sub mymenu
{
print	"<div id='adminmenu'>",
	"<ul><li><a href='index.cgi?logout' class='logout' title='Odhlásit se'>",
		"Odhlásit: <b>$user</b></a></li>",
	"<li><a href='index.cgi?fce=1'",
		(checkaccess(1) ? "" : " class='dismenu'"),
		" title='Plná jména členů'>Plná jména</a></li>",
	"<li><a href='index.cgi?fce=2'",
		(checkaccess(2) ? "" : " class='dismenu'"),
		" title='Data vzniku členství'>Vznik členství</a></li>",
	"<li><a href='index.cgi?fce=3'",
		(checkaccess(3) ? "" : " class='dismenu'"),
		" title='Příspěvky'>Příspěvky</a></li>",
	"<li><a href='index.cgi?fce=4'",
		(checkaccess(4) ? "" : " class='dismenu'"),
		" title='Dlužníci'>Dlužníci</a></li>",
	"<li><a href='index.cgi?fce=5'",
		(checkaccess(5,'w') ? "" : " class='dismenu'"),
		" title='Přidělení členských čísel'>Očíslovat členy</a></li>",
	"<li><a href='index.cgi?fce=6'",
		(checkaccess(6) ? "" : " class='dismenu'"),
		" title='Evidence dokumentů členů'>Dokumenty členů</a></li>",
	"<li><a href='index.cgi?fce=7'",
		(checkaccess(7) ? "" : " class='dismenu'"),
		" title='Kontakty členů'>Kontakty členů</a></li>",
	"<li><a href='index.cgi?fce=8'",
		(checkaccess(8) ? "" : " class='dismenu'"),
		" title='Členství ve skupinách'>Členství ve skupinách</a></li>",
	"<li><a class='regp' href='index.cgi?fce=9'",
		(checkaccess(9) ? "" : " class='dismenu'"),
		" title='Členství ve skupinách'>Kontakty RegP</a></li>",

#	"<li><a href='index.cgi?fce=9' title='Vložit data vzniku členství z Wiki'>Import z Wiki</a></li>",

	"<li><a href='index.cgi?fce=9998'",
		(checkaccess(9998,'w') ? "" : " class='dismenu'"),
		" title='Nastavení práv k aplikaci'>Práva k aplikaci</a></li>",
	"<li><a href='index.cgi?fce=9999'",
		(checkaccess(9999,'w') ? "" : " class='dismenu'"),
		" title='Nastavení aplikace'>Nastavení aplikace</a></li>",
	"</ul><br style='clear: both'>",
	"</div>\n";
}

sub numform
{
my $num=shift;
my $l=length($num);
if($l<=3) {return $num}
if($l<=6) {$num=~s/(\d+?)(\d{3})$/$1 $2/; return $num;}
if($l<=9) {$num=~s/(\d+?)(\d{3}?)(\d{3})$/$1 $2 $3/; return $num;}
if($l<=12) {$num=~s/(\d+?)(\d{3}?)(\d{3}?)(\d{3})$/$1 $2 $3/; return $num;}
$num=~s/(\d+?)(\d{3}?)(\d{3}?)(\d{3}?)(\d{3})$/$1 $2 $3/;
return $num;
}

sub is_ascii
{
my $s=shift;
$ascii=get_setup('ascii_chars','string') unless($ascii);
$s=~s/[$ascii]//sg;
return (length($s)==0);
}

sub to_ascii
{
my $s=shift;
return $s if(length($s)==0);
$ascii=get_setup('ascii_chars','string') unless($ascii);
my $r='';
foreach (split('',$s))
	{
	if($ascii=~m/$_/) {$r.=$_}
	else {$r.='_'}
	}
return $r;
}

sub check_cookies
{
use vars qw/$dbh $user $userid $adminhash $logout/;
my ($id,$hash,$ses,%kuky,$sth);
%kuky = CGI::Cookie->fetch;
unless(defined(%kuky->{ao_admin}))
	{
	return 0;
	}
$user=%kuky->{ao_admin}->{value}->[0];
$ses=%kuky->{ao_admin}->{value}->[1];
param('user',$user);
$sth=$dbh->prepare("select `user_id`,`user_password` from `phpbb_users`
		where `username` like ?");
$sth->execute($user) or die $sth->errstr;
$sth->bind_columns(\($id,$hash));
unless($sth->rows)
	{
	$sth->finish;
	return 0;
	}
$sth->fetch;
$sth->finish;
if(md5_hex($hash,$user) eq $ses)
	{
	$userid=$id;
	$adminhash=$hash;
	my $kuky=new CGI::Cookie(-name => 'ao_admin',
				-value => [$user,$ses],
				-expires => '+' . $logout*1 . 'h',
#				-secure => 1
				);
	print "Set-Cookie: $kuky\n";
	return 1;
	}
$user='';
$userid=0;
return 0;
}
